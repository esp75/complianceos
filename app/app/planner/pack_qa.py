"""Knowledge-pack QA: is every quoted excerpt still on the page it cites?

The pack's value is that every line is sourced. ``load_knowledge`` already checks the schema and the
cross-references; this adds what a loader cannot know:

- **offline**: every citation and source URL is https, and no ``retrieved`` or ``last_verified``
  date is in the future;
- **online**: each cited page is fetched through the Watch's SSRF-hardened ``HttpFetcher`` and the
  excerpt is looked for in the page text.

Matching is on word tokens (Unicode-normalised, case-folded), so markup boundaries, quote styles,
dashes and whitespace do not matter. ``[...]`` or ``…`` in an excerpt marks an omission; every
segment between omissions must appear, in order. Outcomes per citation:

- ``found``: every segment appears;
- ``partial``: not verbatim, but most of the excerpt's five-word runs appear (a footnote marker or
  an amendment inside the text, say). A person should look; it does not fail the run;
- ``not_found``: the page carries some of the excerpt's text but the quote no longer matches, which
  usually means the provision was amended. Fails the run;
- ``unreadable``: the page served none of the excerpt (a bot wall, a page that needs JavaScript, an
  index page, or the wrong URL). A person should open it; it does not fail the run;
- ``blocked`` (HTTP 401/403/429), ``unsupported`` (not HTML or readable PDF), ``unreachable``.

CLI: ``python -m app.planner.pack_qa [--offline] [--jurisdiction xx] [--json out.json]``.
Exit 1 on an offline problem or a ``not_found``.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import re
import sys
import unicodedata
from collections import defaultdict
from enum import StrEnum
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import BaseModel

from app.planner.knowledge import KnowledgeBase, KnowledgeError, load_knowledge
from app.planner.watch import HOST_INTERVAL_S, Fetcher, FetchResult, HttpFetcher, normalise

#: Share of the excerpt's five-word runs that must appear for ``partial``.
PARTIAL_THRESHOLD = 0.6
#: Below this share the page is taken not to show the law text at all (``unreadable``).
UNREADABLE_THRESHOLD = 0.1
_SHINGLE = 5
_OMISSION = re.compile(r"\[\s*(?:\.\.\.|…)\s*\]|…|\.\.\.")
_WORD = re.compile(r"\w+")
_PDF_HYPHEN = re.compile(r"(\w)[-­]\s*\n\s*(\w)")


class Outcome(StrEnum):
    FOUND = "found"
    PARTIAL = "partial"
    NOT_FOUND = "not_found"
    UNREADABLE = "unreadable"
    BLOCKED = "blocked"
    UNSUPPORTED = "unsupported"
    UNREACHABLE = "unreachable"


class CitationCheck(BaseModel):
    citation_id: str
    license_id: str
    url: str
    outcome: Outcome
    #: Share of five-word runs found (1.0 for ``found``); ``None`` when the page was not read.
    coverage: float | None = None
    detail: str = ""


class Report(BaseModel):
    offline_problems: list[str]
    checks: list[CitationCheck]

    def counts(self) -> dict[str, int]:
        out = {o.value: 0 for o in Outcome}
        for c in self.checks:
            out[c.outcome.value] += 1
        return out

    @property
    def failed(self) -> bool:
        return bool(self.offline_problems) or any(c.outcome is Outcome.NOT_FOUND for c in self.checks)


# --- matching ---


def tokens(text: str) -> list[str]:
    return _WORD.findall(unicodedata.normalize("NFKC", text).casefold())


def _contains(hay: list[str], needle: list[str], start: int) -> int:
    """Index just past the first occurrence of ``needle`` in ``hay`` at or after ``start``, or -1."""
    n = len(needle)
    first = needle[0]
    for i in range(start, len(hay) - n + 1):
        if hay[i] == first and hay[i:i + n] == needle:
            return i + n
    return -1


def _shingles(words: list[str]) -> set[tuple[str, ...]]:
    return {tuple(words[i:i + _SHINGLE]) for i in range(len(words) - _SHINGLE + 1)}


def match_excerpt(excerpt: str, page_text: str) -> tuple[Outcome, float]:
    """Look for ``excerpt`` in ``page_text``. Returns the outcome and the five-word-run coverage."""
    page = tokens(page_text)
    segments = [seg for seg in (tokens(s) for s in _OMISSION.split(excerpt)) if seg]
    pos, verbatim = 0, True
    for seg in segments:
        end = _contains(page, seg, pos)
        if end < 0:
            verbatim = False
            break
        pos = end
    if verbatim and segments:
        return Outcome.FOUND, 1.0
    have = _shingles(page)
    hits = total = 0
    for seg in segments:
        if len(seg) < _SHINGLE:  # too short to shingle: count it as one run
            total += 1
            hits += _contains(page, seg, 0) >= 0
            continue
        runs = _shingles(seg)
        total += len(runs)
        hits += len(runs & have)
    coverage = hits / total if total else 0.0
    if coverage >= PARTIAL_THRESHOLD:
        return Outcome.PARTIAL, coverage
    if coverage < UNREADABLE_THRESHOLD:
        return Outcome.UNREADABLE, coverage
    return Outcome.NOT_FOUND, coverage


def page_text(result: FetchResult) -> str:
    if result.text is not None:  # PDF: rejoin words split across lines by hyphenation
        return _PDF_HYPHEN.sub(r"\1\2", result.text)
    return normalise(result.html)


# --- checks ---


def offline_problems(kb: KnowledgeBase, today: dt.date) -> list[str]:
    problems: list[str] = []
    for lic in sorted(kb.licenses.values(), key=lambda x: x.id):
        if lic.last_verified > today:
            problems.append(f"{lic.id}: last_verified {lic.last_verified} is in the future")
        for c in lic.legal_basis:
            if urlsplit(str(c.url)).scheme != "https":
                problems.append(f"{c.id}: citation URL is not https ({c.url})")
            if c.retrieved > today:
                problems.append(f"{c.id}: retrieved {c.retrieved} is in the future")
        for s in lic.sources:
            if urlsplit(str(s.url)).scheme != "https":
                problems.append(f"{lic.id}: source URL is not https ({s.url})")
            if s.retrieved > today:
                problems.append(f"{lic.id}: source retrieved {s.retrieved} is in the future")
    return problems


def _outcome_for_failure(result: FetchResult) -> tuple[Outcome, str]:
    if result.unsupported:
        return Outcome.UNSUPPORTED, result.error
    if result.http_status in (401, 403, 429):
        return Outcome.BLOCKED, result.error
    return Outcome.UNREACHABLE, result.error


async def _fetch_all(urls: list[str], fetcher: Fetcher,
                     host_interval: float) -> dict[str, FetchResult]:
    """Fetch each URL once: hosts in parallel, one request at a time per host, politely spaced."""
    by_host: dict[str, list[str]] = defaultdict(list)
    for u in urls:
        by_host[urlsplit(u).netloc].append(u)
    out: dict[str, FetchResult] = {}

    async def host_worker(host_urls: list[str]) -> None:
        for i, u in enumerate(host_urls):
            if i:
                await asyncio.sleep(host_interval)
            out[u] = await fetcher.fetch(u)

    await asyncio.gather(*(host_worker(v) for v in by_host.values()))
    return out


async def check_pack(kb: KnowledgeBase, fetcher: Fetcher | None, today: dt.date, *,
                     jurisdiction: str | None = None,
                     host_interval: float = HOST_INTERVAL_S) -> Report:
    """Run the offline checks, and the online checks unless ``fetcher`` is ``None``."""
    problems = offline_problems(kb, today)
    lics = sorted((lic for lic in kb.licenses.values()
                   if jurisdiction is None or lic.jurisdiction == jurisdiction), key=lambda x: x.id)
    citations = [(lic.id, c) for lic in lics for c in lic.legal_basis]
    if fetcher is None:
        return Report(offline_problems=problems, checks=[])
    pages = await _fetch_all(sorted({str(c.url) for _, c in citations}), fetcher, host_interval)
    checks: list[CitationCheck] = []
    for lic_id, c in citations:
        result = pages[str(c.url)]
        if not result.ok:
            outcome, detail = _outcome_for_failure(result)
            coverage: float | None = None
        else:
            outcome, cov = match_excerpt(c.excerpt, page_text(result))
            coverage, detail = round(cov, 3), ""
        checks.append(CitationCheck(citation_id=c.id, license_id=lic_id, url=str(c.url),
                                    outcome=outcome, coverage=coverage, detail=detail))
    return Report(offline_problems=problems, checks=checks)


def format_report(report: Report) -> str:
    lines = [f"offline problem: {p}" for p in report.offline_problems]
    for c in report.checks:
        cov = "" if c.coverage is None else f" ({c.coverage:.0%})"
        detail = f" — {c.detail}" if c.detail else ""
        lines.append(f"{c.outcome.value:<12} {c.citation_id}{cov}{detail}")
    counts = ", ".join(f"{k} {v}" for k, v in report.counts().items() if v)
    lines.append(f"{len(report.checks)} citations checked: {counts or 'none'}; "
                 f"{len(report.offline_problems)} offline problems")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Check that the knowledge pack's quotes are still "
                                             "on the pages they cite.")
    ap.add_argument("--offline", action="store_true", help="skip fetching pages")
    ap.add_argument("--jurisdiction", help="only check this jurisdiction's citations")
    ap.add_argument("--json", type=Path, help="also write the report as JSON to this path")
    args = ap.parse_args(argv)
    try:
        kb = load_knowledge()
    except KnowledgeError as exc:
        print(f"the knowledge pack does not load: {exc}", file=sys.stderr)
        return 1
    fetcher = None if args.offline else HttpFetcher()
    report = asyncio.run(check_pack(kb, fetcher, dt.date.today(), jurisdiction=args.jurisdiction))
    print(format_report(report))
    if args.json:
        args.json.write_text(json.dumps(report.model_dump(mode="json"), indent=1), encoding="utf-8")
    return 1 if report.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Knowledge-pack QA harness: excerpt matching, offline checks, outcomes per fetch result."""

from __future__ import annotations

import datetime as dt

import pytest

from app.planner.knowledge import load_knowledge
from app.planner.pack_qa import Outcome, check_pack, match_excerpt, offline_problems, page_text
from app.planner.watch import FetchResult

TODAY = dt.date(2026, 11, 9)
EXCERPT = ("It is unlawful— (a) to establish or use a wireless telegraphy station, except under "
           "and in accordance with a licence (a “wireless telegraphy licence”) granted by OFCOM.")


def test_verbatim_match_ignores_markup_quotes_and_case() -> None:
    page = ("<p>IT IS UNLAWFUL &mdash; (a) to <em>establish</em> or use a wireless telegraphy "
            "station, except under and in accordance with a licence (a \"wireless telegraphy "
            "licence\") granted by OFCOM.</p>")
    from app.planner.watch import normalise
    assert match_excerpt(EXCERPT, normalise(page)) == (Outcome.FOUND, 1.0)


def test_omissions_need_every_segment_in_order() -> None:
    excerpt = "the operator is reliable [...] the operator meets the ITU requirements"
    page = "first the operator is reliable and capable; then the operator meets the ITU requirements"
    assert match_excerpt(excerpt, page)[0] is Outcome.FOUND
    swapped = "the operator meets the ITU requirements, and later the operator is reliable"
    assert match_excerpt(excerpt, swapped)[0] is not Outcome.FOUND


def test_footnote_inside_text_is_partial_not_missing() -> None:
    page = EXCERPT.replace("telegraphy station,", "telegraphy station,[12]")
    page = page.replace("granted by", "granted 3 by")
    outcome, coverage = match_excerpt(EXCERPT, page)
    assert outcome is Outcome.PARTIAL
    assert 0.6 <= coverage < 1.0


def test_page_without_the_text_is_unreadable() -> None:
    outcome, coverage = match_excerpt(EXCERPT, "Cookie settings. Accept all cookies. Contact us.")
    assert outcome is Outcome.UNREADABLE
    assert coverage < 0.1


def test_amended_text_is_not_found() -> None:
    """The law text is on the page but the quoted wording changed: that fails the run."""
    amended = ("It is unlawful to establish or use a wireless telegraphy station except under a "
               "licence issued by the Secretary of State after consulting the regulator.")
    outcome, coverage = match_excerpt(EXCERPT, amended)
    assert outcome is Outcome.NOT_FOUND
    assert 0.1 <= coverage < 0.6


def test_pdf_hyphenation_is_rejoined() -> None:
    result = FetchResult(url="https://x.eu/a.pdf", ok=True,
                         text="a wireless tele-\ngraphy station")
    assert "telegraphy" in page_text(result)


def test_real_pack_has_no_offline_problems() -> None:
    assert offline_problems(load_knowledge(), TODAY) == []


def test_future_retrieval_date_is_reported() -> None:
    kb = load_knowledge()
    problems = offline_problems(kb, dt.date(2026, 1, 1))
    assert any("in the future" in p for p in problems)


class FakeFetcher:
    """Serves each cited page with its excerpts on it, except where told otherwise."""

    def __init__(self, pages: dict[str, FetchResult]) -> None:
        self.pages = pages
        self.calls: list[str] = []

    async def fetch(self, url: str) -> FetchResult:
        self.calls.append(url)
        return self.pages[url]


@pytest.mark.asyncio
async def test_check_pack_outcomes_per_fetch_result() -> None:
    kb = load_knowledge()
    gb = [c for lic in kb.licenses.values() if lic.jurisdiction == "gb" for c in lic.legal_basis]
    urls = sorted({str(c.url) for c in gb})
    assert len(urls) >= 2
    good, *rest = urls
    pages = {u: FetchResult(url=u, ok=True, html="<p>nothing relevant here at all</p>")
             for u in rest}
    assert len(rest) > 1
    # rest[1] shows the law, but the wording no longer matches
    c = next(c for c in gb if str(c.url) == rest[1])
    words = c.excerpt.split()
    pages[rest[1]] = FetchResult(url=rest[1], ok=True, html="<p>" + " ".join(
        w if i % 8 else "amended" for i, w in enumerate(words)) + "</p>")
    pages[good] = FetchResult(url=good, ok=True, html="<p>" + " ".join(
        c.excerpt for c in gb if str(c.url) == good) + "</p>")
    pages[rest[0]] = FetchResult(url=rest[0], ok=False, http_status=403, error="HTTP 403")
    fetcher = FakeFetcher(pages)
    report = await check_pack(kb, fetcher, TODAY, jurisdiction="gb", host_interval=0)
    by_url = {c.url: c.outcome for c in report.checks}
    assert by_url[good] is Outcome.FOUND
    assert by_url[rest[0]] is Outcome.BLOCKED
    assert by_url[rest[1]] is Outcome.NOT_FOUND
    assert all(by_url[u] is Outcome.UNREADABLE for u in rest[2:])
    assert sorted(fetcher.calls) == urls, "each URL fetched once"
    assert report.failed


@pytest.mark.asyncio
async def test_offline_mode_fetches_nothing() -> None:
    report = await check_pack(load_knowledge(), None, TODAY)
    assert report.checks == [] and not report.failed

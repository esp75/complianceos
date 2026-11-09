"""The Watch v0: change detection on the sources the knowledge pack cites (ROADMAP P2, ADR-0019).

The pack's citations are the watch list: every distinct ``citation.url`` is fetched, reduced to its
visible text, hashed, and compared with the hash from the previous successful check. A changed hash
is recorded as a :class:`WatchChange`, linked to the licences that cite the source and, through
them, to the applications a mission is tracking.

What the Watch does not do: it never edits the knowledge pack, never says what a change means in
law, and never reads a URL that is not in the pack. A change means "re-verify the cited provision".
Its baseline is the Watch's own first successful check, not the pack's ``retrieved`` date, so a
change made before the Watch first ran is not detected.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import difflib
import hashlib
import io
import ipaddress
import smtplib
import sys
import uuid
from collections import defaultdict
from collections.abc import Awaitable, Callable, Iterable
from html.parser import HTMLParser
from typing import TYPE_CHECKING, Literal, Protocol
from urllib.parse import urljoin, urlsplit, urlunsplit

import asyncpg
import httpx
from pydantic import BaseModel, Field
from pypdf import PdfReader

from app.config import get_settings
from app.planner.knowledge import KnowledgeBase, load_knowledge

if TYPE_CHECKING:
    from app.planner.store import PlannerStore

USER_AGENT = "ComplianceOS-Watch/0.2 (regulatory source monitor; +open-source)"
REQUEST_TIMEOUT_S = 20.0
HTML_TYPES = frozenset({"text/html", "application/xhtml+xml", "text/plain"})
MAX_BODY_BYTES = 5_000_000
MAX_PDF_BYTES = 25_000_000
PDF_TYPES = frozenset({"application/pdf"})
FEED_TYPES = frozenset({"application/rss+xml", "application/atom+xml", "application/xml", "text/xml"})
#: Stored text kept per source for word-level diffs. The hash covers the full normalised text.
EXCERPT_CHARS = 60_000
#: Seconds between requests to the same host.
HOST_INTERVAL_S = 1.0

# Elements whose text is navigation or code, not regulatory content. Changes in them are ignored.
_SKIP_TAGS = frozenset({"script", "style", "noscript", "template", "svg", "nav", "header", "footer"})


class WatchSource(BaseModel):
    """One URL the pack cites, with everything that cites it."""

    url: str
    citation_ids: list[str]
    license_ids: list[str]
    jurisdictions: list[str]


class FetchResult(BaseModel):
    url: str
    ok: bool
    http_status: int | None = None
    html: str = ""
    #: Plain text already extracted by the fetcher (PDF sources). When set, ``html`` is not used.
    text: str | None = None
    error: str = ""
    #: The source is reachable but not HTML (a PDF, say). The Watch v0 cannot read it; that is not
    #: an outage and is not a change.
    unsupported: bool = False


class SourceState(BaseModel):
    """The Watch's memory of one source. ``body`` is the last *successful* text; an unreachable
    check updates ``status``/``error``/``checked_at`` and keeps the last good hash and text."""

    url: str
    status: Literal["ok", "unreachable", "unsupported"]
    content_hash: str | None = None
    length: int = 0
    body: str = ""
    error: str = ""
    checked_at: dt.datetime


Materiality = Literal["substantive", "editorial", "unclear"]


class WatchChange(BaseModel):
    id: str
    url: str
    kind: Literal["changed", "unreachable", "published"]
    detected_at: dt.datetime
    previous_hash: str | None = None
    new_hash: str | None = None
    size_delta: int = 0
    words_added: int = 0
    words_removed: int = 0
    detail: str = ""
    #: Advisory, from Claude (ADR-0020). None when no model was configured or it failed. The Watch's
    #: own conclusion stays "re-verify"; this only helps a human triage.
    materiality: Materiality | None = None
    ai_summary: str = ""


class RunSummary(BaseModel):
    checked: int = 0
    baselined: int = 0
    unchanged: int = 0
    changed: int = 0
    published: int = 0
    unreachable: int = 0
    unsupported: int = 0
    changes: list[WatchChange] = Field(default_factory=list)


class Fetcher(Protocol):
    async def fetch(self, url: str) -> FetchResult: ...


class WatchStore(Protocol):
    async def get_source_state(self, url: str) -> SourceState | None: ...
    async def save_source_state(self, state: SourceState) -> None: ...
    async def add_watch_change(self, change: WatchChange) -> None: ...
    async def list_watch_changes(self, urls: Iterable[str] | None = None,
                                 limit: int = 200) -> list[WatchChange]: ...


# --- source set (derived from the pack, not configured) ---

def collect_sources(kb: KnowledgeBase) -> list[WatchSource]:
    """Every distinct citation URL in the pack, with the citations, licences and jurisdictions
    that depend on it. Sorted by URL so runs and reports are deterministic."""
    acc: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: {"citations": set(), "licenses": set(), "jurisdictions": set()})
    for lic in kb.licenses.values():
        for cit in lic.legal_basis:
            entry = acc[str(cit.url)]
            entry["citations"].add(cit.id)
            entry["licenses"].add(lic.id)
            entry["jurisdictions"].add(lic.jurisdiction)
    return [
        WatchSource(url=url, citation_ids=sorted(e["citations"]), license_ids=sorted(e["licenses"]),
                    jurisdictions=sorted(e["jurisdictions"]))
        for url, e in sorted(acc.items())
    ]


# --- normalisation ---

class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIP_TAGS:
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)


def normalise(html: str) -> str:
    """Visible text with navigation and code removed and whitespace collapsed. Stable across
    re-renders that only change markup, which is what makes the hash meaningful."""
    parser = _TextExtractor()
    parser.feed(html)
    parser.close()
    return " ".join(" ".join(parser.parts).split())


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def word_diff(old: str, new: str) -> tuple[int, int]:
    """Words added and removed between two excerpts (a coarse size of the change)."""
    a, b = old.split(), new.split()
    added = removed = 0
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if tag in ("replace", "delete"):
            removed += i2 - i1
        if tag in ("replace", "insert"):
            added += j2 - j1
    return added, removed


# --- decision (pure) ---

def decide(prev: SourceState | None, result: FetchResult, now: dt.datetime,
           ) -> tuple[SourceState, WatchChange | None]:
    """The new state of one source, and the change to record if any.

    - Unreachable: never counted as "unchanged". Recorded once per outage (when the source was
      last ``ok``), and the last good hash is kept so recovery is compared with it.
    - First successful check: baseline only, no change.
    - Hash differs from the last good hash: a ``changed`` record with a coarse size.
    """
    if result.unsupported:
        state = SourceState(
            url=result.url, status="unsupported",
            content_hash=prev.content_hash if prev else None,
            length=prev.length if prev else 0,
            body=prev.body if prev else "",
            error=result.error, checked_at=now)
        return state, None

    if not result.ok:
        state = SourceState(
            url=result.url, status="unreachable",
            content_hash=prev.content_hash if prev else None,
            length=prev.length if prev else 0,
            body=prev.body if prev else "",
            error=result.error, checked_at=now)
        change = None
        if prev is None or prev.status == "ok":
            change = WatchChange(id=_id(), url=result.url, kind="unreachable", detected_at=now,
                                 previous_hash=prev.content_hash if prev else None,
                                 detail=result.error)
        return state, change

    text = normalise(result.html) if result.text is None else " ".join(result.text.split())
    digest = content_hash(text)
    state = SourceState(url=result.url, status="ok", content_hash=digest, length=len(text),
                        body=text[:EXCERPT_CHARS], error="", checked_at=now)
    if prev is None or prev.content_hash is None:
        return state, None
    if prev.content_hash == digest:
        return state, None
    added, removed = word_diff(prev.body, state.body)
    change = WatchChange(id=_id(), url=result.url, kind="changed", detected_at=now,
                         previous_hash=prev.content_hash, new_hash=digest,
                         size_delta=len(text) - prev.length, words_added=added,
                         words_removed=removed,
                         detail="source text changed since the last successful check; "
                                "re-verify the cited provision")
    return state, change


def _id() -> str:
    return uuid.uuid4().hex


# --- fetching ---

MAX_REDIRECTS = 5


def _peer_refusal(resp: httpx.Response) -> str | None:
    """Check the address the connection really reached, which closes the gap between the DNS
    answer we validated and the one the connection used (DNS rebinding). The body is not read
    when this refuses. Test transports have no socket, so there is nothing to check."""
    stream = resp.extensions.get("network_stream")
    addr = stream.get_extra_info("server_addr") if stream is not None else None
    if not addr:
        return None
    try:
        ip = ipaddress.ip_address(str(addr[0]).split("%")[0])
    except ValueError:
        return "refused a non-public address"
    return None if ip.is_global else "refused a non-public address"


def _pinned_request(target: str, pinned: str | None) -> tuple[str, dict[str, str] | None]:
    """The URL to connect to and the connection extensions for one hop. With a pinned address the
    connection goes to that IP, while TLS still verifies the certificate for the host name (SNI).
    The Host header is set by the caller, so the server sees the name it expects."""
    if pinned is None:
        return target, None
    parts = urlsplit(target)
    host = parts.hostname or ""
    literal = ":" in pinned
    netloc = (f"[{pinned}]" if literal else pinned) + (f":{parts.port}" if parts.port else "")
    url = urlunsplit((parts.scheme, netloc, parts.path, parts.query, ""))
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return url, {"sni_hostname": host}
    return url, None


class HttpFetcher:
    """Fetches pack URLs over https. Redirects are followed only when they stay on https, and the
    body is capped so a hostile or broken host cannot exhaust memory."""

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport

    async def fetch(self, url: str) -> FetchResult:
        if urlsplit(url).scheme != "https":
            return FetchResult(url=url, ok=False, error="only https sources are watched")
        try:
            async with httpx.AsyncClient(
                    timeout=REQUEST_TIMEOUT_S, follow_redirects=False, transport=self._transport,
                    headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,application/pdf"},
            ) as client:
                target = url  # the logical URL; redirects are joined against this, never a pinned IP
                for _ in range(MAX_REDIRECTS + 1):
                    refusal, pinned = await self._refuse(target)
                    if refusal:
                        return FetchResult(url=url, ok=False, error=refusal)
                    request_url, extensions = _pinned_request(target, pinned)
                    headers = {"Host": urlsplit(target).netloc} if pinned else None
                    async with client.stream("GET", request_url, headers=headers,
                                             extensions=extensions) as resp:
                        if (peer := _peer_refusal(resp)) is not None:
                            return FetchResult(url=url, ok=False, error=peer)
                        if resp.is_redirect and resp.headers.get("location"):
                            target = urljoin(target, resp.headers["location"])
                            continue
                        return await self._read(url, resp)
                return FetchResult(url=url, ok=False, error="too many redirects")
        except httpx.HTTPError as exc:
            return FetchResult(url=url, ok=False, error=type(exc).__name__)

    async def _refuse(self, target: str) -> tuple[str | None, str | None]:
        """Why a hop must not be fetched, and the public address to connect to. Every hop is
        checked, so a redirect cannot lead the Watch to an internal address. The connection then
        goes to the address checked here, so a second DNS answer cannot redirect it (rebinding).
        Returns (refusal, pinned_ip); pinned_ip is None in tests, which have no DNS."""
        parts = urlsplit(target)
        if parts.scheme != "https":
            return "redirected away from https", None
        host = parts.hostname or ""
        if not host or host == "localhost" or host.endswith((".local", ".internal")):
            return "refused a non-public host", None
        try:
            literals = [ipaddress.ip_address(host)]
        except ValueError:
            if self._transport is not None:  # tests: no DNS
                return None, None
            try:
                infos = await asyncio.get_running_loop().getaddrinfo(host, parts.port or 443)
            except OSError:
                return "refused: the host name did not resolve", None
            literals = [ipaddress.ip_address(i[4][0]) for i in infos]
        if not literals or any(not ip.is_global for ip in literals):
            return "refused a non-public address", None
        return None, str(literals[0])

    async def _read(self, url: str, resp: httpx.Response) -> FetchResult:
        if resp.status_code >= 400:
            return FetchResult(url=url, ok=False, http_status=resp.status_code,
                               error=f"HTTP {resp.status_code}")
        ctype = resp.headers.get("content-type", "").split(";")[0].strip().lower()
        if ctype in PDF_TYPES:
            return await self._pdf(url, resp)
        if ctype not in HTML_TYPES | FEED_TYPES:
            return FetchResult(url=url, ok=False, http_status=resp.status_code, unsupported=True,
                               error=f"not HTML ({ctype or 'no content type'}); "
                                     "the Watch reads HTML and PDF")
        body = bytearray()
        async for chunk in resp.aiter_bytes():
            body.extend(chunk)
            if len(body) > MAX_BODY_BYTES:
                return FetchResult(url=url, ok=False, http_status=resp.status_code,
                                   error="response exceeds the size cap")
        html = bytes(body).decode(resp.encoding or "utf-8", errors="replace")
        return FetchResult(url=url, ok=True, http_status=resp.status_code, html=html)

    async def _pdf(self, url: str, resp: httpx.Response) -> FetchResult:
        body = bytearray()
        async for chunk in resp.aiter_bytes():
            body.extend(chunk)
            if len(body) > MAX_PDF_BYTES:
                return FetchResult(url=url, ok=False, http_status=resp.status_code,
                                   error="PDF exceeds the size cap")
        try:
            text = await asyncio.to_thread(pdf_text, bytes(body))
        except Exception as exc:  # pypdf raises many types on damaged files
            return FetchResult(url=url, ok=False, http_status=resp.status_code, unsupported=True,
                               error=f"PDF text could not be read ({type(exc).__name__})")
        if not text.strip():
            return FetchResult(url=url, ok=False, http_status=resp.status_code, unsupported=True,
                               error="PDF has no extractable text (scanned?)")
        return FetchResult(url=url, ok=True, http_status=resp.status_code, text=text)


def pdf_text(data: bytes) -> str:
    """Text of a PDF, page by page. Raises on a damaged or encrypted file."""
    reader = PdfReader(io.BytesIO(data))
    # Many official PDFs are "encrypted" only to forbid copying; they open with an empty password.
    if reader.is_encrypted and not reader.decrypt(""):
        raise ValueError("PDF needs a password")
    return "\n".join(page.extract_text() or "" for page in reader.pages)


# --- run ---

Classifier = Callable[[str, str], Awaitable[tuple[Materiality, str] | None]]


async def run_watch(kb: KnowledgeBase, store: WatchStore, fetcher: Fetcher, now: dt.datetime,
                    *, host_interval: float = HOST_INTERVAL_S,
                    classifier: Classifier | None = None) -> RunSummary:
    """Check every pack source once. Hosts run in parallel; requests to one host are spaced by
    ``host_interval`` seconds so a ministry site is not hammered."""
    by_host: dict[str, list[WatchSource]] = defaultdict(list)
    for src in collect_sources(kb):
        by_host[urlsplit(src.url).netloc].append(src)

    summary = RunSummary()

    async def check_host(sources: list[WatchSource]) -> None:
        for i, src in enumerate(sources):
            if i and host_interval:
                await asyncio.sleep(host_interval)
            result = await fetcher.fetch(src.url)
            prev = await store.get_source_state(src.url)
            state, change = decide(prev, result, now)
            await store.save_source_state(state)
            summary.checked += 1
            if state.status == "unreachable":
                summary.unreachable += 1
            elif state.status == "unsupported":
                summary.unsupported += 1
            elif prev is None or prev.content_hash is None:
                summary.baselined += 1
            elif change is None:
                summary.unchanged += 1
            if change is not None:
                if classifier is not None and change.kind == "changed" and prev is not None:
                    verdict = await classifier(prev.body, state.body)
                    if verdict is not None:
                        change.materiality, change.ai_summary = verdict
                await store.add_watch_change(change)
                summary.changes.append(change)
                if change.kind == "changed":
                    summary.changed += 1

    await asyncio.gather(*(check_host(srcs) for srcs in by_host.values()))
    from app.planner.feeds import run_feeds

    await run_feeds(kb, store, fetcher, now, summary, host_interval=host_interval)
    summary.changes.sort(key=lambda c: (c.url, c.detail))
    return summary


# --- command line (for cron / compose; ADR-0019) ---

def format_summary(summary: RunSummary) -> str:
    lines = [f"checked {summary.checked}: {summary.baselined} baselined, {summary.unchanged} unchanged, "
             f"{summary.changed} changed, {summary.published} published, {summary.unreachable} unreachable, "
             f"{summary.unsupported} unsupported"]
    for c in summary.changes:
        if c.kind == "changed":
            lines.append(f"  changed      {c.url}  (+{c.words_added}/-{c.words_removed} words)")
        elif c.kind == "published":
            lines.append(f"  published    {c.url}  ({c.detail})")
        else:
            lines.append(f"  unreachable  {c.url}  ({c.detail})")
    return "\n".join(lines)


async def _alert(kb: KnowledgeBase, store: PlannerStore, summary: RunSummary) -> int:
    """Email the changes this run found, one digest for all workspaces' tracked applications.
    Changes are already recorded, so a failed send loses nothing: the exit code reports it."""
    from app.planner.alerts import AlertConfig, send_digest
    from app.planner.digest import watch_items

    cfg = AlertConfig.from_settings(get_settings())
    if cfg is None:
        print("alerts are not configured (COMPLIANCEOS_SMTP_HOST and _ALERT_FROM)",
              file=sys.stderr)
        return 2
    failed = False
    sent_items = 0
    for workspace in await store.list_workspaces():
        items = await watch_items(store, workspace, kb, None, changes=summary.changes)
        if not items:
            continue
        # A workspace's own recipients win; the deployment list is only the fallback, so one
        # tenant's digest goes to another tenant's people only if nobody configured otherwise.
        own = await store.alert_recipients(workspace)
        target = cfg.model_copy(update={"recipients": own}) if own else cfg
        if not target.recipients:
            continue
        try:
            if await send_digest(target, items):
                sent_items += len(items)
        except (OSError, smtplib.SMTPException) as exc:
            failed = True
            print(f"alert email failed for a workspace ({type(exc).__name__}); changes are recorded",
                  file=sys.stderr)
    if failed:
        return 1
    print(f"alert sent: {sent_items} item(s)" if sent_items else "no tracked application affected; no alert")
    return 0


async def _cli(cmd: str, dsn: str, alert: bool = False) -> int:
    from app.planner.store import PostgresPlannerStore

    kb = load_knowledge()
    store = PostgresPlannerStore(dsn)
    try:
        await store.connect()
    except (OSError, asyncpg.PostgresError) as exc:
        print(f"cannot reach the planner database ({type(exc).__name__}); "
              "set COMPLIANCEOS_PLANNER_DSN", file=sys.stderr)
        return 1
    try:
        await store.apply_schema()
        if cmd == "run":
            settings = get_settings()
            async with httpx.AsyncClient(timeout=60) as http:
                classifier = None
                if settings.anthropic_api_key:  # Anthropic EU endpoint only (ADR-0010)
                    from app.llm.anthropic_eu import AnthropicEUClient
                    from app.planner.classify import make_classifier

                    classifier = make_classifier(AnthropicEUClient(
                        settings.anthropic_api_key, settings.anthropic_model, http,
                        base_url=settings.anthropic_base_url))
                summary = await run_watch(kb, store, HttpFetcher(), dt.datetime.now(dt.UTC),
                                          classifier=classifier)
            print(format_summary(summary))
            if alert:
                return await _alert(kb, store, summary)
        else:
            for c in await store.list_watch_changes(limit=50):
                print(f"{c.detected_at:%Y-%m-%d %H:%M} {c.kind:<11} {c.url}  {c.detail}")
    finally:
        await store.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.planner.watch",
                                     description="Check the sources the knowledge pack cites.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="check every cited source once and record changes")
    run.add_argument("--alert", action="store_true",
                     help="email a digest of changes that touch tracked applications")
    sub.add_parser("changes", help="list the most recent recorded changes")
    args = parser.parse_args(argv)

    settings = get_settings()
    dsn = settings.planner_dsn or settings.kg_dsn
    if not dsn:
        print("the Watch needs Postgres: set COMPLIANCEOS_PLANNER_DSN", file=sys.stderr)
        return 2
    return asyncio.run(_cli(args.cmd, dsn, alert=getattr(args, "alert", False)))


if __name__ == "__main__":
    raise SystemExit(main())

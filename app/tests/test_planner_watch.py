"""The Watch v0 (ADR-0019): normalisation, change detection, source set, and a full run against a
fake fetcher and the in-memory store. No network."""

from __future__ import annotations

import datetime as dt
from collections.abc import AsyncIterator, Iterator
from email.message import EmailMessage

import httpx
import pytest
from fastapi import FastAPI

from app.api import planner
from app.config import get_settings
from app.planner.alerts import AlertConfig, send_digest
from app.planner.knowledge import Feed, load_knowledge
from app.planner.store import MemoryPlannerStore
from app.planner.watch import (
    FetchResult,
    HttpFetcher,
    SourceState,
    WatchChange,
    collect_sources,
    content_hash,
    decide,
    normalise,
    run_watch,
    word_diff,
)

KB = load_knowledge()
NOW = dt.datetime(2026, 11, 1, 9, 0, tzinfo=dt.UTC)
LATER = NOW + dt.timedelta(days=1)
URL = "https://example.gov/licence-rules"


def page(body: str, *, nav: str = "Home | News", extra: str = "") -> str:
    return (f"<html><head><title>x</title><script>var t=1;</script><style>p{{}}</style></head>"
            f"<body><nav>{nav}</nav><main><p>{body}</p>{extra}</main>"
            f"<footer>© 2026</footer></body></html>")


def ok(html: str, url: str = URL) -> FetchResult:
    return FetchResult(url=url, ok=True, http_status=200, html=html)


def down(error: str = "HTTP 503", url: str = URL) -> FetchResult:
    return FetchResult(url=url, ok=False, error=error)


# --- normalisation ---

def test_normalise_keeps_content_and_drops_chrome() -> None:
    # <title> is content (kept); script, style, nav and footer are not.
    text = normalise(page("Operators  must\n\n apply &amp; wait."))
    assert text == "x Operators must apply & wait."


def test_markup_and_navigation_changes_do_not_change_the_hash() -> None:
    a = normalise(page("Operators must apply.", nav="Home"))
    b = normalise(page("Operators must apply.", nav="Home | Contact | New banner"))
    c = normalise("<html><head><title>x</title></head><body>"
                  "<div class='a'><p>Operators   must\napply.</p></div></body></html>")
    assert content_hash(a) == content_hash(b) == content_hash(c)


def test_word_diff_counts_added_and_removed_words() -> None:
    assert word_diff("a b c d", "a b x y z") == (3, 2)
    assert word_diff("same text", "same text") == (0, 0)


# --- decision ---

def test_first_successful_check_is_a_baseline_not_a_change() -> None:
    state, change = decide(None, ok(page("v1")), NOW)
    assert state.status == "ok" and change is None


def test_same_content_is_unchanged() -> None:
    first, _ = decide(None, ok(page("v1")), NOW)
    _, change = decide(first, ok(page("v1")), LATER)
    assert change is None


def test_changed_text_is_recorded_with_size() -> None:
    first, _ = decide(None, ok(page("The licence fee is 100 euros.")), NOW)
    state, change = decide(first, ok(page("The licence fee is 250 euros.")), LATER)
    assert change is not None and change.kind == "changed"
    assert change.previous_hash == first.content_hash
    assert change.new_hash == state.content_hash != first.content_hash
    assert change.words_added == 1 and change.words_removed == 1
    assert "re-verify" in change.detail


def test_outage_is_never_reported_as_unchanged() -> None:
    first, _ = decide(None, ok(page("v1")), NOW)
    state, change = decide(first, down(), LATER)
    assert state.status == "unreachable"
    assert change is not None and change.kind == "unreachable"
    assert change.detail == "HTTP 503"


def test_repeated_outage_is_recorded_once() -> None:
    first, _ = decide(None, ok(page("v1")), NOW)
    down_state, first_outage = decide(first, down(), LATER)
    _, second = decide(down_state, down(), LATER + dt.timedelta(days=1))
    assert first_outage is not None
    assert second is None


def test_outage_keeps_last_good_hash_so_recovery_is_compared_with_it() -> None:
    first, _ = decide(None, ok(page("v1")), NOW)
    down_state, _ = decide(first, down(), LATER)
    assert down_state.content_hash == first.content_hash
    _, same = decide(down_state, ok(page("v1")), LATER)
    assert same is None
    _, changed = decide(down_state, ok(page("v2 changed")), LATER)
    assert changed is not None and changed.kind == "changed"


def test_outage_before_any_success_then_first_success_is_baseline() -> None:
    down_state, outage = decide(None, down(), NOW)
    assert outage is not None and outage.kind == "unreachable"
    state, change = decide(down_state, ok(page("v1")), LATER)
    assert state.status == "ok" and change is None


def test_non_html_source_is_unsupported_not_an_outage_or_a_change() -> None:
    first, _ = decide(None, ok(page("v1")), NOW)
    state, change = decide(first, FetchResult(url=URL, ok=False, unsupported=True,
                                              error="not HTML (application/pdf)"), LATER)
    assert state.status == "unsupported"
    assert state.content_hash == first.content_hash
    assert change is None


def test_only_the_bounded_excerpt_is_stored_but_the_hash_covers_everything() -> None:
    long = "word " * 40_000
    state, _ = decide(None, ok(page(long)), NOW)
    assert len(state.body) <= 60_000
    assert state.length > len(state.body)


# --- source set ---

def test_source_set_is_exactly_the_citation_urls_in_the_pack() -> None:
    sources = collect_sources(KB)
    cited = {str(c.url) for lic in KB.licenses.values() for c in lic.legal_basis}
    assert {s.url for s in sources} == cited
    assert len(sources) == len(cited)


def test_each_source_links_back_to_its_licences_and_citations() -> None:
    for src in collect_sources(KB):
        assert src.license_ids and src.citation_ids
        for lic_id in src.license_ids:
            lic = KB.licenses[lic_id]
            assert any(str(c.url) == src.url for c in lic.legal_basis)


def test_sources_are_sorted_for_deterministic_runs() -> None:
    urls = [s.url for s in collect_sources(KB)]
    assert urls == sorted(urls)


# --- fetcher safety ---

async def test_only_https_is_fetched() -> None:
    result = await HttpFetcher().fetch("http://example.gov/rules")
    assert not result.ok
    assert "https" in result.error


def _mock(status: int, ctype: str, body: bytes = b"<p>ok</p>") -> HttpFetcher:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, headers={"content-type": ctype}, content=body)
    return HttpFetcher(transport=httpx.MockTransport(handler))


def _pdf_bytes(text: str) -> bytes:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(text=text)
    return bytes(pdf.output())


async def test_pdf_text_is_extracted_and_hashed_like_html() -> None:
    fetched = await _mock(200, "application/pdf", _pdf_bytes("Fee is 100 euros")).fetch(URL)
    assert fetched.ok and fetched.text is not None and "Fee is 100 euros" in fetched.text
    first, _ = decide(None, fetched, NOW)
    other = await _mock(200, "application/pdf", _pdf_bytes("Fee is 250 euros")).fetch(URL)
    _, change = decide(first, other, LATER)
    assert change is not None and change.kind == "changed"


async def test_unreadable_pdf_is_unsupported_not_an_outage() -> None:
    result = await _mock(200, "application/pdf", b"%PDF-1.7 garbage").fetch(URL)
    assert not result.ok and result.unsupported
    assert "PDF" in result.error


async def test_other_content_types_are_unsupported() -> None:
    result = await _mock(200, "application/msword", b"x").fetch(URL)
    assert not result.ok and result.unsupported and "not HTML" in result.error


async def test_html_is_read_and_http_errors_are_outages() -> None:
    html = await _mock(200, "text/html; charset=utf-8").fetch(URL)
    assert html.ok and "ok" in html.html
    forbidden = await _mock(403, "text/html").fetch(URL)
    assert not forbidden.ok and not forbidden.unsupported
    assert forbidden.error == "HTTP 403"


# --- full run ---

class FakeFetcher:
    """Serves one HTML body per URL; URLs missing from ``pages`` are unreachable."""

    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages
        self.calls: list[str] = []

    async def fetch(self, url: str) -> FetchResult:
        self.calls.append(url)
        if url in self.pages:
            return ok(self.pages[url], url=url)
        return down("HTTP 404", url=url)


def atom(*entries: tuple[str, str]) -> str:
    items = "".join(f"<entry><id>urn:{i}</id><title>{t}</title>"
                    f"<link rel='self' href='http://x/self/{i}'/><link href='https://x/{i}'/></entry>"
                    for i, t in entries)
    return f"<feed xmlns='http://www.w3.org/2005/Atom'><title>f</title>{items}</feed>"


FEED_URLS = [str(f.url) for j in KB.jurisdictions.values() for f in j.feeds]


@pytest.fixture
def pages() -> dict[str, str]:
    served = {str(c.url): page(f"text of {c.id}") for lic in KB.licenses.values()
              for c in lic.legal_basis}
    served.update({u: atom(("1", "Unrelated notice")) for u in FEED_URLS})
    return served


async def test_first_run_baselines_every_source_and_reports_no_changes(
        pages: dict[str, str]) -> None:
    store = MemoryPlannerStore()
    summary = await run_watch(KB, store, FakeFetcher(pages), NOW, host_interval=0)
    assert summary.checked == len(collect_sources(KB)) + len(FEED_URLS)
    assert summary.baselined == summary.checked
    assert summary.changes == []


async def test_second_run_detects_only_the_source_that_moved(pages: dict[str, str]) -> None:
    store = MemoryPlannerStore()
    await run_watch(KB, store, FakeFetcher(pages), NOW, host_interval=0)
    moved_url = sorted(u for u in pages if u not in FEED_URLS)[0]
    pages[moved_url] = page("completely new wording")
    summary = await run_watch(KB, store, FakeFetcher(pages), LATER, host_interval=0)
    assert summary.changed == 1
    assert [c.url for c in summary.changes] == [moved_url]
    stored = await store.list_watch_changes([moved_url])
    assert len(stored) == 1 and stored[0].kind == "changed"


async def test_unreachable_source_is_counted_separately_from_unchanged(
        pages: dict[str, str]) -> None:
    store = MemoryPlannerStore()
    await run_watch(KB, store, FakeFetcher(pages), NOW, host_interval=0)
    gone = sorted(u for u in pages if u not in FEED_URLS)[0]
    del pages[gone]
    summary = await run_watch(KB, store, FakeFetcher(pages), LATER, host_interval=0)
    assert summary.unreachable == 1
    assert summary.unchanged == summary.checked - 1
    state = await store.get_source_state(gone)
    assert isinstance(state, SourceState) and state.status == "unreachable"


async def test_run_only_fetches_pack_urls(pages: dict[str, str]) -> None:
    fetcher = FakeFetcher(pages)
    await run_watch(KB, MemoryPlannerStore(), fetcher, NOW, host_interval=0)
    assert set(fetcher.calls) == set(pages)


# --- API: the Watch against tracked applications ---

CLIENT = {"X-ComplianceOS-Client": "test"}
WATCHED_LICENSE = "lu-space-activity-authorisation"


@pytest.fixture(autouse=True)
def local_mode(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("CELESTIA_AUTH_MODE", "local")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
async def client(pages: dict[str, str]) -> AsyncIterator[httpx.AsyncClient]:
    from app.planner.store import MemoryPlannerStore

    app = FastAPI()
    app.state.knowledge = KB
    app.state.planner_store = MemoryPlannerStore()
    app.state.llm = None
    app.state.watch_fetcher = FakeFetcher(pages)
    app.state.watch_host_interval = 0
    app.state.watch_min_interval = 0
    app.include_router(planner.router)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost",
                                 headers=CLIENT) as c:
        yield c


async def test_change_surfaces_only_for_the_workspace_tracking_the_licence(
        client: httpx.AsyncClient, pages: dict[str, str]) -> None:
    mid = (await client.post("/missions/sample")).json()["id"]
    created = await client.post(f"/missions/{mid}/applications", json={"license_id": WATCHED_LICENSE})
    assert created.status_code == 201, created.text
    app_id = created.json()["application"]["id"]

    assert (await client.get("/watch/changes")).json() == []
    baseline = await client.post("/watch/run")
    assert baseline.status_code == 200 and baseline.json()["changed"] == 0

    moved = sorted(str(c.url) for c in KB.licenses[WATCHED_LICENSE].legal_basis)[0]
    pages[moved] = page("new wording after an amendment")
    run = (await client.post("/watch/run")).json()
    assert run["changed"] == 1

    items = (await client.get("/watch/changes")).json()
    assert len(items) == 1
    item = items[0]
    assert item["change"]["url"] == moved and item["change"]["kind"] == "changed"
    assert WATCHED_LICENSE in item["license_ids"]
    assert [a["application_id"] for a in item["affected"]] == [app_id]
    assert "re-verify" in item["advice"].lower()

    mission_view = await client.get(f"/missions/{mid}/watch")
    assert mission_view.status_code == 200 and len(mission_view.json()) == 1

    other = (await client.post("/missions/sample")).json()["id"]
    assert (await client.get(f"/missions/{other}/watch")).json() == []
    assert (await client.get("/missions/does-not-exist/watch")).status_code == 404


# --- alert email (ADR-0020) ---

async def _tracked_change(store: MemoryPlannerStore, pages: dict[str, str]) -> list[WatchChange]:
    from app.planner.sample import sample_mission

    mission = await store.create_mission("local", sample_mission(NOW.date()))
    await store.create_application("local", mission.id, WATCHED_LICENSE)
    await run_watch(KB, store, FakeFetcher(pages), NOW, host_interval=0)
    moved = sorted(str(c.url) for c in KB.licenses[WATCHED_LICENSE].legal_basis)[0]
    pages[moved] = page("new wording after an amendment")
    summary = await run_watch(KB, store, FakeFetcher(pages), LATER, host_interval=0)
    return summary.changes


def _cfg() -> AlertConfig:
    return AlertConfig(host="smtp.example.eu", port=587, sender="watch@example.eu",
                       recipients=["ops@example.eu"], web_url="https://planner.example.eu")


async def test_digest_is_sent_for_changes_touching_tracked_applications(
        pages: dict[str, str]) -> None:
    from app.planner.digest import watch_items

    store = MemoryPlannerStore()
    changes = await _tracked_change(store, pages)
    items = await watch_items(store, "local", KB, None, changes=changes)
    sent: list[EmailMessage] = []
    assert await send_digest(_cfg(), items, lambda cfg, msg: sent.append(msg))
    (msg,) = sent
    assert msg["To"] == "ops@example.eu" and "1 source change" in msg["Subject"]
    body = msg.get_content()
    assert WATCHED_LICENSE in body and "Re-verify" in body
    assert "https://planner.example.eu" in body


async def test_no_email_when_no_tracked_application_is_affected(pages: dict[str, str]) -> None:
    from app.planner.digest import watch_items

    store = MemoryPlannerStore()
    await run_watch(KB, store, FakeFetcher(pages), NOW, host_interval=0)
    pages[sorted(u for u in pages if u not in FEED_URLS)[0]] = page("changed")
    summary = await run_watch(KB, store, FakeFetcher(pages), LATER, host_interval=0)
    assert summary.changed == 1
    items = await watch_items(store, "local", KB, None, changes=summary.changes)
    sent: list[EmailMessage] = []
    assert not await send_digest(_cfg(), items, lambda cfg, msg: sent.append(msg))
    assert sent == []


def test_alerts_are_off_until_fully_configured() -> None:
    from app.config import Settings

    assert AlertConfig.from_settings(Settings(smtp_host="h")) is None
    cfg = AlertConfig.from_settings(Settings(smtp_host="h", alert_from="a@x.eu",
                                             alert_recipients="b@x.eu, c@x.eu"))
    assert cfg is not None and cfg.recipients == ["b@x.eu", "c@x.eu"]


# --- advisory classification (ADR-0020) ---

class FakeLLM:
    def __init__(self, reply: str = "", fail: bool = False) -> None:
        self.reply, self.fail, self.prompts = reply, fail, []  # type: list[str]

    async def complete(self, system: str, prompt: str, *, max_tokens: int = 1024) -> str:
        from app.llm.base import LLMError

        self.prompts.append(prompt)
        if self.fail:
            raise LLMError("down")
        return self.reply


async def test_change_is_classified_from_the_differing_passages_only(
        pages: dict[str, str]) -> None:
    from app.planner.classify import make_classifier

    llm = FakeLLM('Sure: {"materiality": "substantive", "summary": "Fee raised."}')
    store = MemoryPlannerStore()
    await run_watch(KB, store, FakeFetcher(pages), NOW, host_interval=0)
    pages[sorted(u for u in pages if u not in FEED_URLS)[0]] = page("The fee is now 250 euros.")
    summary = await run_watch(KB, store, FakeFetcher(pages), LATER, host_interval=0,
                              classifier=make_classifier(llm))
    (change,) = summary.changes
    assert change.materiality == "substantive" and change.ai_summary == "Fee raised."
    assert len(llm.prompts) == 1 and "[added]" in llm.prompts[0]
    assert "text of" not in llm.prompts[0].split("[context]")[0]


async def test_model_failure_or_garbage_leaves_the_change_unclassified(
        pages: dict[str, str]) -> None:
    from app.planner.classify import make_classifier

    for llm in (FakeLLM(fail=True), FakeLLM("no json here"),
                FakeLLM('{"materiality": "scary", "summary": "x"}')):
        store = MemoryPlannerStore()
        pages_now = dict(pages)
        await run_watch(KB, store, FakeFetcher(pages_now), NOW, host_interval=0)
        pages_now[sorted(u for u in pages_now if u not in FEED_URLS)[0]] = page("changed wording")
        summary = await run_watch(KB, store, FakeFetcher(pages_now), LATER, host_interval=0,
                                  classifier=make_classifier(llm))
        (change,) = summary.changes
        assert change.kind == "changed" and change.materiality is None


async def test_no_classifier_means_no_model_call(pages: dict[str, str]) -> None:
    store = MemoryPlannerStore()
    await run_watch(KB, store, FakeFetcher(pages), NOW, host_interval=0)
    pages[sorted(u for u in pages if u not in FEED_URLS)[0]] = page("changed wording")
    summary = await run_watch(KB, store, FakeFetcher(pages), LATER, host_interval=0)
    assert summary.changes[0].materiality is None


# --- publication feeds (ADR-0020) ---

FEED_LICENSE = "gb-orbital-operator-licence"


def _feed(license_id: str) -> tuple[str, Feed]:
    for j in KB.jurisdictions.values():
        for f in j.feeds:
            if license_id in f.license_ids:
                return str(f.url), f
    raise AssertionError(license_id)


def test_feed_parsing_reads_rss_and_atom() -> None:
    from app.planner.feeds import parse_feed

    rss = ("<rss version='2.0'><channel><title>t</title><item><title>Space rule</title>"
           "<link>https://x/1</link><guid>g1</guid><description>about satellites</description>"
           "</item></channel></rss>")
    (e,) = parse_feed(rss)
    assert (e.key, e.title, e.link) == ("g1", "Space rule", "https://x/1")
    (a,) = parse_feed(atom(("7", "Atom entry")))
    assert a.key == "urn:7" and a.link == "https://x/7"  # not the rel=self link
    with pytest.raises(ValueError):
        parse_feed("<html><body>not a feed</body></html>")
    with pytest.raises(ValueError):
        parse_feed("<!DOCTYPE x [<!ENTITY a 'b'>]><rss>&a;</rss>")  # entities are refused


async def test_feed_reports_only_new_matching_entries_after_a_baseline(
        pages: dict[str, str]) -> None:
    url, feed = _feed(FEED_LICENSE)
    keyword = feed.keywords[0]
    store = MemoryPlannerStore()
    pages[url] = atom(("1", f"Old {keyword} order"))
    base = await run_watch(KB, store, FakeFetcher(pages), NOW, host_interval=0)
    assert base.published == 0  # the baseline never alerts, even though an entry matches

    pages[url] = atom(("1", f"Old {keyword} order"), ("2", f"New {keyword} regulations"),
                      ("3", "Unrelated fisheries notice"))
    run = await run_watch(KB, store, FakeFetcher(pages), LATER, host_interval=0)
    published = [c for c in run.changes if c.kind == "published"]
    assert run.published == 1 and len(published) == 1
    assert published[0].url == url and f"New {keyword} regulations" in published[0].detail

    again = await run_watch(KB, store, FakeFetcher(pages), LATER + dt.timedelta(days=1),
                            host_interval=0)
    assert again.published == 0  # already seen


async def test_published_entry_reaches_the_workspace_tracking_the_licence(
        pages: dict[str, str]) -> None:
    from app.planner.digest import watch_items
    from app.planner.sample import sample_mission

    url, feed = _feed(FEED_LICENSE)
    keyword = feed.keywords[0]
    store = MemoryPlannerStore()
    mission = await store.create_mission("local", sample_mission(NOW.date()))
    await store.create_application("local", mission.id, FEED_LICENSE)
    pages[url] = atom(("1", "Old"))
    await run_watch(KB, store, FakeFetcher(pages), NOW, host_interval=0)
    pages[url] = atom(("1", "Old"), ("2", f"{keyword} amendment"))
    run = await run_watch(KB, store, FakeFetcher(pages), LATER, host_interval=0)
    (item,) = await watch_items(store, "local", KB, None, changes=run.changes)
    assert item.change.kind == "published" and item.affected[0].license_id == FEED_LICENSE


async def test_unparseable_feed_is_an_outage_not_a_baseline(pages: dict[str, str]) -> None:
    url, _ = _feed(FEED_LICENSE)
    store = MemoryPlannerStore()
    pages[url] = "<html>blocked</html>"
    run = await run_watch(KB, store, FakeFetcher(pages), NOW, host_interval=0)
    state = await store.get_source_state(url)
    assert state is not None and state.status == "unreachable" and run.unreachable >= 1


def test_every_feed_licence_belongs_to_its_jurisdiction() -> None:
    for j in KB.jurisdictions.values():
        for f in j.feeds:
            assert all(KB.licenses[lid].jurisdiction == j.id for lid in f.license_ids)


async def test_manual_run_is_rate_limited_and_not_concurrent(client: httpx.AsyncClient) -> None:
    """Review finding: any writer could hammer POST /watch/run (fetches, LLM calls, racing runs)."""
    transport = client._transport  # type: ignore[attr-defined]
    app = transport.app
    app.state.watch_min_interval = 3600
    assert (await client.post("/watch/run")).status_code == 200
    assert (await client.post("/watch/run")).status_code == 429

    app.state.watch_min_interval = 0
    lock = app.state.watch_lock
    await lock.acquire()
    try:
        assert (await client.post("/watch/run")).status_code == 409
    finally:
        lock.release()


# --- per-workspace alert recipients ---

async def test_recipients_api_validates_and_cleans(client: httpx.AsyncClient) -> None:
    got = (await client.get("/alerts/recipients")).json()
    assert got == {"recipients": [], "fallback_to_deployment_list": True}
    ok = await client.put("/alerts/recipients",
                          json={"recipients": [" Ops@Client.eu ", "ops@client.eu", "b@c.eu"]})
    assert ok.status_code == 200 and ok.json()["recipients"] == ["ops@client.eu", "b@c.eu"]
    assert (await client.get("/alerts/recipients")).json()["fallback_to_deployment_list"] is False
    for bad in (["a@b.eu\nBcc: x@y.eu"], ["Name <a@b.eu>"], ["a@b.eu, c@d.eu"], ["nope"],
                [f"u{i}@x.eu" for i in range(21)]):
        assert (await client.put("/alerts/recipients", json={"recipients": bad})).status_code == 422


async def test_digest_goes_to_each_workspaces_own_recipients(
        monkeypatch: pytest.MonkeyPatch, pages: dict[str, str]) -> None:
    from app.planner import alerts as alerts_mod
    from app.planner.sample import sample_mission
    from app.planner.watch import _alert

    monkeypatch.setenv("CELESTIA_SMTP_HOST", "smtp.test")
    monkeypatch.setenv("CELESTIA_ALERT_FROM", "watch@x.eu")
    monkeypatch.setenv("CELESTIA_ALERT_RECIPIENTS", "default@x.eu")
    get_settings.cache_clear()
    store = MemoryPlannerStore()
    for ws in ("tenant-a", "tenant-b", "tenant-c"):
        m = await store.create_mission(ws, sample_mission(NOW.date()))
        await store.create_application(ws, m.id, WATCHED_LICENSE)
    await store.set_alert_recipients("tenant-a", ["a@a.eu"])
    await store.set_alert_recipients("tenant-b", ["b@b.eu"])  # tenant-c falls back to default

    await run_watch(KB, store, FakeFetcher(pages), NOW, host_interval=0)
    moved = sorted(str(c.url) for c in KB.licenses[WATCHED_LICENSE].legal_basis)[0]
    pages[moved] = page("new wording after an amendment")
    summary = await run_watch(KB, store, FakeFetcher(pages), LATER, host_interval=0)

    sent: list[tuple[str, ...]] = []

    async def fake_send(cfg: AlertConfig, items: list[object], sender: object = None) -> bool:
        sent.append(tuple(cfg.recipients))
        return True

    monkeypatch.setattr(alerts_mod, "send_digest", fake_send)
    assert await _alert(KB, store, summary) == 0
    assert sorted(sent) == [("a@a.eu",), ("b@b.eu",), ("default@x.eu",)]
    get_settings.cache_clear()


@pytest.mark.parametrize("target", [
    "https://127.0.0.1/admin", "https://10.0.0.5/x", "https://169.254.169.254/latest/meta-data",
    "https://[::1]/x", "https://localhost/x", "https://db.internal/x",
])
async def test_redirect_to_internal_address_is_refused(target: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "example.gov":
            return httpx.Response(302, headers={"location": target})
        raise AssertionError(f"the fetcher followed the redirect to {request.url}")
    result = await HttpFetcher(transport=httpx.MockTransport(handler)).fetch("https://example.gov/a")
    assert not result.ok and "refused" in (result.error or "")


async def test_redirect_to_public_https_is_followed_and_loops_end() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/a":
            return httpx.Response(301, headers={"location": "/b"})
        if request.url.path == "/loop":
            return httpx.Response(302, headers={"location": "/loop"})
        return httpx.Response(200, headers={"content-type": "text/html"}, content=b"<p>ok</p>")
    f = HttpFetcher(transport=httpx.MockTransport(handler))
    assert (await f.fetch("https://example.gov/a")).ok
    loop = await f.fetch("https://example.gov/loop")
    assert not loop.ok and "redirect" in (loop.error or "")


def test_smtp_refuses_cleartext_credentials() -> None:
    from app.planner.alerts import smtp_send
    cfg = AlertConfig(host="mail.example.com", port=25, user="u", password="p", security="none",
                      sender="a@x.eu", recipients=["b@x.eu"])
    with pytest.raises(ValueError, match="clear text"):
        smtp_send(cfg, EmailMessage())
    with pytest.raises(ValueError, match="unknown SMTP security"):
        smtp_send(cfg.model_copy(update={"security": "tls"}), EmailMessage())

"""Official publication feeds (ADR-0020): new instruments that match a curated keyword list.

A feed is checked like a page: the first successful read is a baseline; afterwards every entry
not seen before whose title or summary contains one of the feed's keywords is recorded as a
``published`` change on the feed URL. The set of seen entry ids is kept in the source state, so
no schema change is needed. The Watch reports that something new was published, not what it means."""

from __future__ import annotations

import asyncio
import datetime as dt
from collections import defaultdict
from urllib.parse import urlsplit

from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException

from app.planner.knowledge import Feed, KnowledgeBase
from app.planner.watch import (
    Fetcher,
    FetchResult,
    RunSummary,
    SourceState,
    WatchChange,
    WatchSource,
    WatchStore,
    _id,
    content_hash,
    decide,
)

#: Entry ids remembered per feed. Feeds list recent entries only, so this bounds the state.
MAX_SEEN = 2000


class Entry:
    __slots__ = ("key", "link", "text", "title")

    def __init__(self, key: str, title: str, link: str, text: str) -> None:
        self.key, self.title, self.link, self.text = key, title, link, text


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_feed(xml: str) -> list[Entry]:
    """Entries of an RSS 2.0 or Atom feed. Raises ValueError on anything that is not a feed."""
    try:
        root = ElementTree.fromstring(xml.encode("utf-8"))
    except (ElementTree.ParseError, DefusedXmlException) as exc:
        raise ValueError("not a readable feed") from exc
    entries: list[Entry] = []
    for node in root.iter():
        if _local(node.tag) not in ("item", "entry"):
            continue
        fields: dict[str, str] = {}
        for child in node:
            name = _local(child.tag)
            if name == "link":
                href = child.get("href") or (child.text or "").strip()
                rel = child.get("rel")
                if href and rel is None:
                    fields.setdefault("link", href)
                elif href and rel == "alternate" and child.get("type", "").startswith("text/html"):
                    fields.setdefault("link_alt", href)
            elif name in ("title", "guid", "id", "description", "summary"):
                fields.setdefault(name, " ".join((child.text or "").split()))
        title = fields.get("title", "")
        link = fields.get("link") or fields.get("link_alt", "")
        key = fields.get("guid") or fields.get("id") or link or title
        if key:
            entries.append(Entry(key, title, link,
                                 f"{title} {fields.get('description', '')} {fields.get('summary', '')}"))
    if not entries and _local(root.tag) not in ("rss", "feed", "RDF"):
        raise ValueError("not a feed")
    return entries


def matches(entry: Entry, keywords: list[str]) -> bool:
    haystack = entry.text.lower()
    return any(k.lower() in haystack for k in keywords)


def collect_feeds(kb: KnowledgeBase) -> list[WatchSource]:
    """Feeds as watch sources, tied to the licences they were curated for."""
    out = [WatchSource(url=str(f.url), citation_ids=[], license_ids=sorted(f.license_ids),
                       jurisdictions=[j.id])
           for j in kb.jurisdictions.values() for f in j.feeds]
    return sorted(out, key=lambda s: s.url)


def decide_feed(prev: SourceState | None, result: FetchResult, feed: Feed,
                now: dt.datetime) -> tuple[SourceState, list[WatchChange]]:
    url = str(feed.url)
    if not result.ok:
        state, change = decide(prev, result, now)
        return state, [change] if change else []
    try:
        entries = parse_feed(result.html if result.text is None else result.text)
    except ValueError:
        bad = FetchResult(url=url, ok=False, error="feed could not be parsed")
        state, change = decide(prev, bad, now)
        return state, [change] if change else []
    previous = set(prev.body.split("\n")) if prev and prev.content_hash else None
    keys = [e.key for e in entries]
    merged = list(dict.fromkeys(keys + (prev.body.split("\n") if prev else [])))[:MAX_SEEN]
    body = "\n".join(k for k in merged if k)
    state = SourceState(url=url, status="ok", content_hash=content_hash(body), length=len(entries),
                        body=body, error="", checked_at=now)
    if previous is None:
        return state, []
    changes = [
        WatchChange(id=_id(), url=url, kind="published", detected_at=now,
                    detail=f"{e.title or e.key} — {e.link}".strip(" —"))
        for e in entries if e.key not in previous and matches(e, feed.keywords)]
    return state, changes


async def run_feeds(kb: KnowledgeBase, store: WatchStore, fetcher: Fetcher, now: dt.datetime,
                    summary: RunSummary, *, host_interval: float) -> None:
    by_host: dict[str, list[Feed]] = defaultdict(list)
    for j in kb.jurisdictions.values():
        for f in j.feeds:
            by_host[urlsplit(str(f.url)).netloc].append(f)

    async def check_host(feeds: list[Feed]) -> None:
        for i, feed in enumerate(feeds):
            if i and host_interval:
                await asyncio.sleep(host_interval)
            result = await fetcher.fetch(str(feed.url))
            prev = await store.get_source_state(str(feed.url))
            state, changes = decide_feed(prev, result, feed, now)
            await store.save_source_state(state)
            summary.checked += 1
            if state.status == "unreachable":
                summary.unreachable += 1
            elif state.status == "unsupported":
                summary.unsupported += 1
            elif prev is None or prev.content_hash is None:
                summary.baselined += 1
            elif not changes:
                summary.unchanged += 1
            for change in changes:
                await store.add_watch_change(change)
                summary.changes.append(change)
                if change.kind == "published":
                    summary.published += 1

    await asyncio.gather(*(check_host(fs) for fs in by_host.values()))

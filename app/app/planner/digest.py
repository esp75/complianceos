"""Which tracked applications does a source change touch? (ADR-0019)

Shared by the web API (``/watch/changes``) and the alert emails, so the two always agree."""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import BaseModel

from app.planner.feeds import collect_feeds
from app.planner.knowledge import KnowledgeBase
from app.planner.store import PlannerStore
from app.planner.tracker import Application, AppStatus
from app.planner.watch import WatchChange, collect_sources

ADVICE = "Re-verify the cited provision before relying on it; the Watch does not judge the change."


class WatchAffected(BaseModel):
    application_id: str
    mission_id: str
    license_id: str
    status: AppStatus


class WatchItem(BaseModel):
    """A source change, and the tracked applications of this workspace whose licences cite it.
    ``advice`` is the only conclusion the Watch draws: re-verify the cited provision."""

    change: WatchChange
    license_ids: list[str]
    citation_ids: list[str]
    jurisdictions: list[str]
    affected: list[WatchAffected]
    advice: str = ADVICE


async def watch_items(store: PlannerStore, workspace: str, kb: KnowledgeBase,
                      mission_ids: list[str] | None,
                      changes: Iterable[WatchChange] | None = None) -> list[WatchItem]:
    """Changes touching this workspace's tracked applications. ``changes`` limits the result to
    those records (the alert path passes the ones a run just found); default is every recorded one."""
    if mission_ids is None:
        mission_ids = [m.id for m in await store.list_missions(workspace)]
    apps: list[Application] = []
    for mid in mission_ids:
        apps.extend(await store.list_applications(workspace, mid))
    if not apps:
        return []
    tracked = {a.license_id for a in apps}
    sources = {s.url: s for s in [*collect_sources(kb), *collect_feeds(kb)]
               if tracked & set(s.license_ids)}
    recorded = list(changes) if changes is not None else await store.list_watch_changes(
        urls=sources.keys())
    items: list[WatchItem] = []
    for change in recorded:
        src = sources.get(change.url)
        if src is None:
            continue
        items.append(WatchItem(
            change=change, license_ids=src.license_ids, citation_ids=src.citation_ids,
            jurisdictions=src.jurisdictions,
            affected=[WatchAffected(application_id=a.id, mission_id=a.mission_id,
                                    license_id=a.license_id, status=a.status)
                      for a in apps if a.license_id in src.license_ids]))
    return [i for i in items if i.affected]

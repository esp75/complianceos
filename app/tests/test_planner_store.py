"""Store contract: the same behaviour from the in-memory and the Postgres planner stores.

The Postgres run is opt-in: set COMPLIANCEOS_PG_TEST_DSN to a scratch database, e.g.
``postgresql://postgres:password@127.0.0.1:55433/kg``. Each run uses fresh workspace ids, so it
never touches other data.
"""

from __future__ import annotations

import datetime as dt
import os
import uuid
from collections.abc import AsyncIterator

import pytest

from app.planner.sample import sample_mission
from app.planner.store import DuplicateError, MemoryPlannerStore, PlannerStore, PostgresPlannerStore
from app.planner.tracker import AppStatus, ContactIn, apply_update
from app.planner.watch import FetchResult, decide

TODAY = dt.date(2026, 10, 15)
PG_DSN = os.environ.get("COMPLIANCEOS_PG_TEST_DSN")


@pytest.fixture(params=["memory", "postgres"])
async def store(request: pytest.FixtureRequest) -> AsyncIterator[PlannerStore]:
    if request.param == "memory":
        yield MemoryPlannerStore()
        return
    if not PG_DSN:
        pytest.skip("set COMPLIANCEOS_PG_TEST_DSN to run the Postgres store contract")
    pg = PostgresPlannerStore(PG_DSN)
    await pg.connect()
    await pg.apply_schema()
    await pg.apply_schema()  # idempotent
    try:
        yield pg
    finally:
        await pg.close()


def ws() -> str:
    return f"test-{uuid.uuid4().hex[:12]}"


async def test_mission_round_trip(store: PlannerStore) -> None:
    w = ws()
    m = await store.create_mission(w, sample_mission(TODAY))
    got = await store.get_mission(w, m.id)
    assert got is not None and got.profile == m.profile
    assert [x.id for x in await store.list_missions(w)] == [m.id]
    changed = m.profile.model_copy(update={"satellite_count": 12})
    updated = await store.update_mission(w, m.id, changed)
    assert updated is not None and updated.profile.satellite_count == 12


async def test_workspaces_are_isolated(store: PlannerStore) -> None:
    a, b = ws(), ws()
    m = await store.create_mission(a, sample_mission(TODAY))
    app = await store.create_application(a, m.id, "itu-notification")
    assert await store.get_mission(b, m.id) is None
    assert await store.update_mission(b, m.id, m.profile) is None
    assert await store.get_application(b, app.id) is None
    assert await store.list_applications(b, m.id) == []
    assert await store.list_events(b, app.id) == []
    with pytest.raises(KeyError):
        await store.create_application(b, m.id, "itu-advance-publication")
    with pytest.raises(KeyError):
        await store.add_contact(b, app.id, ContactIn(on_date=TODAY, channel="email",
                                                     counterpart="x", summary="y"))
    assert not await store.delete_mission(b, m.id)
    assert await store.get_mission(a, m.id) is not None


async def test_application_events_and_contacts(store: PlannerStore) -> None:
    w = ws()
    m = await store.create_mission(w, sample_mission(TODAY))
    app = await store.create_application(w, m.id, "lu-space-activity-authorisation")
    with pytest.raises(DuplicateError):
        await store.create_application(w, m.id, "lu-space-activity-authorisation")

    sub = apply_update(app, status=AppStatus.SUBMITTED, submitted_on=dt.date(2026, 9, 1),
                       granted_on=None, today=TODAY)
    saved = await store.save_application(w, sub.model_copy(update={"reference": "R-1", "owner": "Dana"}),
                                         "status", app.status, "filed")
    assert saved.status == AppStatus.SUBMITTED and saved.reference == "R-1" and saved.owner == "Dana"
    assert saved.submitted_on == dt.date(2026, 9, 1)

    c = await store.add_contact(w, app.id, ContactIn(
        on_date=dt.date(2026, 10, 1), channel="meeting", counterpart="LSA", summary="kick-off",
        next_step="send docs", next_step_due=dt.date(2026, 11, 1)))
    assert c.next_step_due == dt.date(2026, 11, 1)
    assert [x.id for x in await store.list_contacts(w, app.id)] == [c.id]

    events = await store.list_events(w, app.id)
    assert [e.kind for e in events] == ["created", "status", "contact"]
    assert events[1].from_status == AppStatus.NOT_STARTED and events[1].to_status == AppStatus.SUBMITTED

    assert await store.delete_mission(w, m.id)
    assert await store.get_application(w, app.id) is None


async def test_watch_state_and_changes_round_trip(store: PlannerStore) -> None:
    # The Watch tables are global (public sources), so every run uses a fresh URL.
    url = f"https://example.gov/{uuid.uuid4().hex}"
    now = dt.datetime(2026, 11, 1, 9, 0, tzinfo=dt.UTC)
    first, none = decide(None, FetchResult(url=url, ok=True, html="<p>rule one</p>"), now)
    assert none is None
    await store.save_source_state(first)
    assert await store.get_source_state(url) == first

    state, change = decide(first, FetchResult(url=url, ok=True, html="<p>rule two</p>"),
                           now + dt.timedelta(days=1))
    assert change is not None
    await store.save_source_state(state)
    await store.add_watch_change(change)
    assert await store.get_source_state(url) == state
    assert await store.list_watch_changes([url]) == [change]
    assert await store.list_watch_changes([f"https://example.gov/{uuid.uuid4().hex}"]) == []


async def test_history_checkpoints_and_workspace_listing(store: PlannerStore) -> None:
    w = f"w-{uuid.uuid4().hex}"
    assert await store.last_history_root(w) is None
    await store.create_mission(w, sample_mission(TODAY))
    assert w in await store.list_workspaces()
    await store.add_history_checkpoint(w, "aa" * 32, None, 3)
    await store.add_history_checkpoint(w, "bb" * 32, "aa" * 32, 5)
    assert await store.last_history_root(w) == "bb" * 32
    assert await store.last_history_root(f"w-{uuid.uuid4().hex}") is None
    # Watch changes carry the advisory triage fields through storage.
    url = f"https://example.gov/{uuid.uuid4().hex}"
    from app.planner.watch import WatchChange
    c = WatchChange(id=uuid.uuid4().hex, url=url, kind="changed",
                    detected_at=dt.datetime(2026, 11, 1, tzinfo=dt.UTC), materiality="substantive",
                    ai_summary="Fee raised.")
    await store.add_watch_change(c)
    assert await store.list_watch_changes([url]) == [c]


async def test_usage_events_round_trip(store: PlannerStore) -> None:
    w = f"w-{uuid.uuid4().hex}"
    at = dt.datetime(2026, 11, 1, 9, tzinfo=dt.UTC)
    await store.add_usage_event(w, "local", "session_start", at)
    got = await store.usage_events(w, at - dt.timedelta(days=1))
    assert [(k, a) for k, a in got] == [("session_start", at)]
    assert await store.usage_events(w, at + dt.timedelta(days=1)) == []


async def test_alert_recipients_are_per_workspace(store: PlannerStore) -> None:
    a, b = f"w-{uuid.uuid4().hex}", f"w-{uuid.uuid4().hex}"
    assert await store.alert_recipients(a) == []
    await store.set_alert_recipients(a, ["ops@a.eu", "legal@a.eu"])
    await store.set_alert_recipients(b, ["x@b.eu"])
    await store.set_alert_recipients(b, ["y@b.eu"])  # replaces
    assert await store.alert_recipients(a) == ["ops@a.eu", "legal@a.eu"]
    assert await store.alert_recipients(b) == ["y@b.eu"]
    await store.set_alert_recipients(a, [])
    assert await store.alert_recipients(a) == []

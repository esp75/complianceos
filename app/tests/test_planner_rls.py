"""Row-level security on the planner tables (opt-in Postgres contract, ROADMAP P3).

The store's queries already filter by workspace; these tests go around them and check that the
database itself refuses cross-workspace rows. Set COMPLIANCEOS_PG_TEST_DSN to a scratch database
(the compose default connects as a superuser, so this also checks the role switch).
"""

from __future__ import annotations

import datetime as dt
import os
import uuid
from collections.abc import AsyncIterator

import asyncpg
import pytest

from app.api.rls import planner_policies as rls
from app.planner.sample import sample_mission
from app.planner.store import PostgresPlannerStore
from app.planner.tracker import ContactIn

PG_DSN = os.environ.get("COMPLIANCEOS_PG_TEST_DSN")
TODAY = dt.date(2026, 11, 9)


@pytest.fixture
async def store() -> AsyncIterator[PostgresPlannerStore]:
    if not PG_DSN:
        pytest.skip("set COMPLIANCEOS_PG_TEST_DSN to run the RLS contract")
    pg = PostgresPlannerStore(PG_DSN)
    await pg.connect()
    await pg.apply_schema()
    yield pg
    await pg.close()


async def _seed(store: PostgresPlannerStore) -> tuple[str, str, str]:
    """Workspace A with a mission, an application and a contact. Returns (ws_a, mission, app)."""
    ws = f"rls-a-{uuid.uuid4().hex}"
    m = await store.create_mission(ws, sample_mission(TODAY))
    a = await store.create_application(ws, m.id, "itu-coordination-request")
    await store.add_contact(ws, a.id, ContactIn(on_date=TODAY, channel="email",
                                                counterpart="BR", summary="filed"))
    return ws, m.id, a.id


async def _as_store_role(store: PostgresPlannerStore, workspace: str | None,
                         sql: str, *args: object) -> list[asyncpg.Record]:
    """Run raw SQL the way the store's connections run it, with no workspace filter in the SQL."""
    async with store._p().acquire() as conn, conn.transaction():
        if workspace is not None:
            await conn.execute(rls.SET_WORKSPACE_SQL, workspace)
        return list(await conn.fetch(sql, *args))


@pytest.mark.asyncio
async def test_store_connections_do_not_bypass_rls(store: PostgresPlannerStore) -> None:
    async with store._p().acquire() as conn:
        assert not await conn.fetchval(
            "SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = current_user")


@pytest.mark.asyncio
async def test_unfiltered_query_sees_only_its_workspace(store: PostgresPlannerStore) -> None:
    ws_a, mission_a, app_a = await _seed(store)
    ws_b = f"rls-b-{uuid.uuid4().hex}"
    for table in ("planner_mission", "planner_application", "planner_application_event",
                  "planner_contact"):
        rows = await _as_store_role(store, ws_b, f"SELECT * FROM {table}")
        assert rows == [], f"{table}: workspace B saw rows"
    seen = await _as_store_role(store, ws_a, "SELECT id FROM planner_mission")
    assert [r["id"] for r in seen] == [mission_a]
    apps = await _as_store_role(store, ws_a, "SELECT id FROM planner_application")
    assert [r["id"] for r in apps] == [app_a]


@pytest.mark.asyncio
async def test_no_workspace_set_sees_nothing(store: PostgresPlannerStore) -> None:
    await _seed(store)
    for table in (*rls.WORKSPACE_TABLES, *(t for t, _, _ in rls.CHILD_TABLES)):
        assert await _as_store_role(store, None, f"SELECT * FROM {table}") == [], table


@pytest.mark.asyncio
async def test_cannot_write_into_another_workspace(store: PostgresPlannerStore) -> None:
    ws_a, mission_a, app_a = await _seed(store)
    ws_b = f"rls-b-{uuid.uuid4().hex}"
    with pytest.raises(asyncpg.InsufficientPrivilegeError):  # WITH CHECK violation
        await _as_store_role(store, ws_b,
                             "INSERT INTO planner_mission (id, workspace, profile) "
                             "VALUES ($1, $2, '{}'::jsonb)", uuid.uuid4().hex, ws_a)
    with pytest.raises(asyncpg.InsufficientPrivilegeError):
        await _as_store_role(store, ws_b,
                             "INSERT INTO planner_application (id, mission_id, license_id, status) "
                             "VALUES ($1, $2, 'x', 'not_started')", uuid.uuid4().hex, mission_a)
    updated = await _as_store_role(store, ws_b,
                                   "UPDATE planner_application SET notes = 'x' WHERE id = $1 "
                                   "RETURNING id", app_a)
    assert updated == []


@pytest.mark.asyncio
async def test_workspace_setting_does_not_outlive_the_transaction(
        store: PostgresPlannerStore) -> None:
    ws_a, _, _ = await _seed(store)
    async with store._p().acquire() as conn:
        async with conn.transaction():
            await conn.execute(rls.SET_WORKSPACE_SQL, ws_a)
        assert await conn.fetch("SELECT * FROM planner_mission") == []


@pytest.mark.asyncio
async def test_alert_job_still_lists_workspaces(store: PostgresPlannerStore) -> None:
    ws_a, _, _ = await _seed(store)
    assert ws_a in await store.list_workspaces()

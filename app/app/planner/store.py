"""Planner persistence: missions, applications, their event log and contact log (ADR-0018).

One interface, two implementations:

- :class:`PostgresPlannerStore` — the real store (asyncpg), sharing the kg-postgres instance unless
  ``CELESTIA_PLANNER_DSN`` points elsewhere.
- :class:`MemoryPlannerStore` — process memory, used by tests and as a fallback so the planner
  still runs with no database at all (data is lost on restart; ``/readyz`` says so).

Every read and write is scoped to a workspace: a mission belongs to one workspace, and
applications, events and contacts are only reachable through their mission. The event log is
append-only — there is no code path that edits or deletes an event.
"""

from __future__ import annotations

import datetime as dt
import itertools
import json
import uuid
from typing import Literal, Protocol, cast

import asyncpg
from pydantic import BaseModel

from app.planner.mission import MissionProfile
from app.planner.tracker import Application, ApplicationEvent, AppStatus, Contact, ContactIn

PLANNER_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS planner_mission (
    id          TEXT PRIMARY KEY,
    workspace   TEXT NOT NULL,
    profile     JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS planner_mission_ws_idx ON planner_mission (workspace, created_at);

CREATE TABLE IF NOT EXISTS planner_application (
    id            TEXT PRIMARY KEY,
    mission_id    TEXT NOT NULL REFERENCES planner_mission (id) ON DELETE CASCADE,
    license_id    TEXT NOT NULL,
    status        TEXT NOT NULL,
    submitted_on  DATE,
    granted_on    DATE,
    reference     TEXT NOT NULL DEFAULT '',
    notes         TEXT NOT NULL DEFAULT '',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (mission_id, license_id)
);

CREATE TABLE IF NOT EXISTS planner_application_event (
    id              BIGSERIAL PRIMARY KEY,
    application_id  TEXT NOT NULL REFERENCES planner_application (id) ON DELETE CASCADE,
    at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    kind            TEXT NOT NULL,
    from_status     TEXT,
    to_status       TEXT,
    note            TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS planner_event_app_idx ON planner_application_event (application_id, id);

CREATE TABLE IF NOT EXISTS planner_contact (
    id              BIGSERIAL PRIMARY KEY,
    application_id  TEXT NOT NULL REFERENCES planner_application (id) ON DELETE CASCADE,
    on_date         DATE NOT NULL,
    channel         TEXT NOT NULL,
    counterpart     TEXT NOT NULL,
    summary         TEXT NOT NULL,
    next_step       TEXT NOT NULL DEFAULT '',
    next_step_due   DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS planner_contact_app_idx ON planner_contact (application_id, on_date);
"""

EventKind = Literal["created", "status", "update", "contact"]


class Mission(BaseModel):
    id: str
    workspace: str
    profile: MissionProfile
    created_at: dt.datetime
    updated_at: dt.datetime


class DuplicateError(ValueError):
    """Raised when a mission already tracks an application for a licence."""


class PlannerStore(Protocol):
    kind: str

    async def create_mission(self, workspace: str, profile: MissionProfile) -> Mission: ...
    async def list_missions(self, workspace: str) -> list[Mission]: ...
    async def get_mission(self, workspace: str, mission_id: str) -> Mission | None: ...
    async def update_mission(self, workspace: str, mission_id: str,
                             profile: MissionProfile) -> Mission | None: ...
    async def delete_mission(self, workspace: str, mission_id: str) -> bool: ...
    async def create_application(self, workspace: str, mission_id: str,
                                 license_id: str) -> Application: ...
    async def list_applications(self, workspace: str, mission_id: str) -> list[Application]: ...
    async def get_application(self, workspace: str, app_id: str) -> Application | None: ...
    async def save_application(self, workspace: str, app: Application, kind: EventKind,
                               from_status: AppStatus | None, note: str) -> Application: ...
    async def list_events(self, workspace: str, app_id: str) -> list[ApplicationEvent]: ...
    async def add_contact(self, workspace: str, app_id: str, contact: ContactIn) -> Contact: ...
    async def list_contacts(self, workspace: str, app_id: str) -> list[Contact]: ...


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _new_id() -> str:
    return uuid.uuid4().hex


class MemoryPlannerStore:
    kind = "memory"

    def __init__(self) -> None:
        self._missions: dict[str, Mission] = {}
        self._apps: dict[str, Application] = {}
        self._events: list[ApplicationEvent] = []
        self._contacts: list[Contact] = []
        self._seq = itertools.count(1)

    def _owns(self, workspace: str, mission_id: str) -> bool:
        m = self._missions.get(mission_id)
        return m is not None and m.workspace == workspace

    def _event(self, app_id: str, kind: EventKind, from_status: AppStatus | None,
               to_status: AppStatus | None, note: str) -> None:
        self._events.append(ApplicationEvent(
            id=next(self._seq), application_id=app_id, at=_now(), kind=kind,
            from_status=from_status, to_status=to_status, note=note))

    async def create_mission(self, workspace: str, profile: MissionProfile) -> Mission:
        now = _now()
        m = Mission(id=_new_id(), workspace=workspace, profile=profile, created_at=now, updated_at=now)
        self._missions[m.id] = m
        return m

    async def list_missions(self, workspace: str) -> list[Mission]:
        return sorted((m for m in self._missions.values() if m.workspace == workspace),
                      key=lambda m: m.created_at, reverse=True)

    async def get_mission(self, workspace: str, mission_id: str) -> Mission | None:
        return self._missions[mission_id] if self._owns(workspace, mission_id) else None

    async def update_mission(self, workspace: str, mission_id: str,
                             profile: MissionProfile) -> Mission | None:
        if not self._owns(workspace, mission_id):
            return None
        m = self._missions[mission_id].model_copy(update={"profile": profile, "updated_at": _now()})
        self._missions[mission_id] = m
        return m

    async def delete_mission(self, workspace: str, mission_id: str) -> bool:
        if not self._owns(workspace, mission_id):
            return False
        del self._missions[mission_id]
        gone = {a.id for a in self._apps.values() if a.mission_id == mission_id}
        self._apps = {k: v for k, v in self._apps.items() if k not in gone}
        self._events = [e for e in self._events if e.application_id not in gone]
        self._contacts = [c for c in self._contacts if c.application_id not in gone]
        return True

    async def create_application(self, workspace: str, mission_id: str,
                                 license_id: str) -> Application:
        if not self._owns(workspace, mission_id):
            raise KeyError(mission_id)
        if any(a.mission_id == mission_id and a.license_id == license_id for a in self._apps.values()):
            raise DuplicateError(license_id)
        now = _now()
        app = Application(id=_new_id(), mission_id=mission_id, license_id=license_id,
                          created_at=now, updated_at=now)
        self._apps[app.id] = app
        self._event(app.id, "created", None, app.status, "")
        return app

    async def list_applications(self, workspace: str, mission_id: str) -> list[Application]:
        if not self._owns(workspace, mission_id):
            return []
        return sorted((a for a in self._apps.values() if a.mission_id == mission_id),
                      key=lambda a: a.created_at)

    async def get_application(self, workspace: str, app_id: str) -> Application | None:
        a = self._apps.get(app_id)
        return a if a and self._owns(workspace, a.mission_id) else None

    async def save_application(self, workspace: str, app: Application, kind: EventKind,
                               from_status: AppStatus | None, note: str) -> Application:
        if await self.get_application(workspace, app.id) is None:
            raise KeyError(app.id)
        saved = app.model_copy(update={"updated_at": _now()})
        self._apps[app.id] = saved
        self._event(app.id, kind, from_status, saved.status, note)
        return saved

    async def list_events(self, workspace: str, app_id: str) -> list[ApplicationEvent]:
        if await self.get_application(workspace, app_id) is None:
            return []
        return [e for e in self._events if e.application_id == app_id]

    async def add_contact(self, workspace: str, app_id: str, contact: ContactIn) -> Contact:
        if await self.get_application(workspace, app_id) is None:
            raise KeyError(app_id)
        c = Contact(id=next(self._seq), application_id=app_id, created_at=_now(),
                    **contact.model_dump())
        self._contacts.append(c)
        self._event(app_id, "contact", None, None, f"{contact.channel} with {contact.counterpart}")
        return c

    async def list_contacts(self, workspace: str, app_id: str) -> list[Contact]:
        if await self.get_application(workspace, app_id) is None:
            return []
        return sorted((c for c in self._contacts if c.application_id == app_id),
                      key=lambda c: (c.on_date, c.id))


def _mission(row: asyncpg.Record) -> Mission:
    profile = row["profile"]
    return Mission(
        id=row["id"], workspace=row["workspace"],
        profile=MissionProfile.model_validate(json.loads(profile) if isinstance(profile, str) else profile),
        created_at=row["created_at"], updated_at=row["updated_at"],
    )


def _application(row: asyncpg.Record) -> Application:
    return Application(**{k: row[k] for k in (
        "id", "mission_id", "license_id", "status", "submitted_on", "granted_on", "reference",
        "notes", "created_at", "updated_at")})


_APP_COLS = ("a.id, a.mission_id, a.license_id, a.status, a.submitted_on, a.granted_on, "
             "a.reference, a.notes, a.created_at, a.updated_at")


class PostgresPlannerStore:
    kind = "postgres"

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=5)

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    def _p(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("planner store not connected")
        return self._pool

    async def apply_schema(self) -> None:
        async with self._p().acquire() as conn:
            await conn.execute(PLANNER_SCHEMA_SQL)

    async def create_mission(self, workspace: str, profile: MissionProfile) -> Mission:
        row = await self._p().fetchrow(
            "INSERT INTO planner_mission (id, workspace, profile) VALUES ($1, $2, $3::jsonb) "
            "RETURNING *", _new_id(), workspace, profile.model_dump_json())
        return _mission(row)

    async def list_missions(self, workspace: str) -> list[Mission]:
        rows = await self._p().fetch(
            "SELECT * FROM planner_mission WHERE workspace = $1 ORDER BY created_at DESC", workspace)
        return [_mission(r) for r in rows]

    async def get_mission(self, workspace: str, mission_id: str) -> Mission | None:
        row = await self._p().fetchrow(
            "SELECT * FROM planner_mission WHERE workspace = $1 AND id = $2", workspace, mission_id)
        return _mission(row) if row else None

    async def update_mission(self, workspace: str, mission_id: str,
                             profile: MissionProfile) -> Mission | None:
        row = await self._p().fetchrow(
            "UPDATE planner_mission SET profile = $3::jsonb, updated_at = now() "
            "WHERE workspace = $1 AND id = $2 RETURNING *",
            workspace, mission_id, profile.model_dump_json())
        return _mission(row) if row else None

    async def delete_mission(self, workspace: str, mission_id: str) -> bool:
        result = await self._p().execute(
            "DELETE FROM planner_mission WHERE workspace = $1 AND id = $2", workspace, mission_id)
        return cast(str, result).endswith(" 1")

    async def create_application(self, workspace: str, mission_id: str,
                                 license_id: str) -> Application:
        async with self._p().acquire() as conn, conn.transaction():
            if not await conn.fetchval("SELECT 1 FROM planner_mission WHERE workspace = $1 AND id = $2",
                                       workspace, mission_id):
                raise KeyError(mission_id)
            try:
                row = await conn.fetchrow(
                    "INSERT INTO planner_application (id, mission_id, license_id, status) "
                    "VALUES ($1, $2, $3, $4) RETURNING *",
                    _new_id(), mission_id, license_id, AppStatus.NOT_STARTED.value)
            except asyncpg.UniqueViolationError as exc:
                raise DuplicateError(license_id) from exc
            await conn.execute(
                "INSERT INTO planner_application_event (application_id, kind, to_status) "
                "VALUES ($1, 'created', $2)", row["id"], AppStatus.NOT_STARTED.value)
        return _application(row)

    async def list_applications(self, workspace: str, mission_id: str) -> list[Application]:
        rows = await self._p().fetch(
            f"SELECT {_APP_COLS} FROM planner_application a JOIN planner_mission m "
            "ON m.id = a.mission_id WHERE m.workspace = $1 AND a.mission_id = $2 "
            "ORDER BY a.created_at", workspace, mission_id)
        return [_application(r) for r in rows]

    async def get_application(self, workspace: str, app_id: str) -> Application | None:
        row = await self._p().fetchrow(
            f"SELECT {_APP_COLS} FROM planner_application a JOIN planner_mission m "
            "ON m.id = a.mission_id WHERE m.workspace = $1 AND a.id = $2", workspace, app_id)
        return _application(row) if row else None

    async def save_application(self, workspace: str, app: Application, kind: EventKind,
                               from_status: AppStatus | None, note: str) -> Application:
        async with self._p().acquire() as conn, conn.transaction():
            row = await conn.fetchrow(
                "UPDATE planner_application a SET status = $3, submitted_on = $4, granted_on = $5, "
                "reference = $6, notes = $7, updated_at = now() FROM planner_mission m "
                "WHERE m.id = a.mission_id AND m.workspace = $1 AND a.id = $2 "
                f"RETURNING {_APP_COLS}",
                workspace, app.id, app.status.value, app.submitted_on, app.granted_on,
                app.reference, app.notes)
            if row is None:
                raise KeyError(app.id)
            await conn.execute(
                "INSERT INTO planner_application_event (application_id, kind, from_status, "
                "to_status, note) VALUES ($1, $2, $3, $4, $5)",
                app.id, kind, from_status.value if from_status else None, app.status.value, note)
        return _application(row)

    async def list_events(self, workspace: str, app_id: str) -> list[ApplicationEvent]:
        rows = await self._p().fetch(
            "SELECT e.* FROM planner_application_event e JOIN planner_application a "
            "ON a.id = e.application_id JOIN planner_mission m ON m.id = a.mission_id "
            "WHERE m.workspace = $1 AND e.application_id = $2 ORDER BY e.id", workspace, app_id)
        return [ApplicationEvent(**dict(r)) for r in rows]

    async def add_contact(self, workspace: str, app_id: str, contact: ContactIn) -> Contact:
        async with self._p().acquire() as conn, conn.transaction():
            owned = await conn.fetchval(
                "SELECT 1 FROM planner_application a JOIN planner_mission m ON m.id = a.mission_id "
                "WHERE m.workspace = $1 AND a.id = $2", workspace, app_id)
            if not owned:
                raise KeyError(app_id)
            row = await conn.fetchrow(
                "INSERT INTO planner_contact (application_id, on_date, channel, counterpart, "
                "summary, next_step, next_step_due) VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING *",
                app_id, contact.on_date, contact.channel, contact.counterpart, contact.summary,
                contact.next_step, contact.next_step_due)
            await conn.execute(
                "INSERT INTO planner_application_event (application_id, kind, note) "
                "VALUES ($1, 'contact', $2)", app_id, f"{contact.channel} with {contact.counterpart}")
        return Contact(**dict(row))

    async def list_contacts(self, workspace: str, app_id: str) -> list[Contact]:
        rows = await self._p().fetch(
            "SELECT c.* FROM planner_contact c JOIN planner_application a ON a.id = c.application_id "
            "JOIN planner_mission m ON m.id = a.mission_id "
            "WHERE m.workspace = $1 AND c.application_id = $2 ORDER BY c.on_date, c.id",
            workspace, app_id)
        return [Contact(**dict(r)) for r in rows]

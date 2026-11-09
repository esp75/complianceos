# MARKED-FOR-EXTERNAL-REVIEW — Trail of Bits / Quarkslab / Cure53
"""Postgres row-level security for the planner's workspace data (ROADMAP P3).

The planner store already scopes every query by workspace. These policies make the database refuse
cross-workspace rows as well, so one missing ``WHERE workspace = ...`` cannot leak another client's
licensing state. They are defence in depth against query bugs, not against code that controls the
connection: code in the API process can still ``RESET ROLE``.

How it is enforced:

- Each workspace-scoped call runs in a transaction that sets ``app.workspace`` with
  ``set_config(..., true)``, so the setting dies with the transaction and cannot leak to the next
  user of a pooled connection.
- Tables with a ``workspace`` column match it against that setting. Applications, events and
  contacts have no workspace column; their policies require the parent row to be visible, and the
  parent is itself filtered, so visibility follows the mission.
- With the setting unset, ``current_setting('app.workspace', true)`` is NULL and nothing matches:
  the policies fail closed.
- ``FORCE ROW LEVEL SECURITY`` makes the policies apply to the table owner too. Superusers and
  ``BYPASSRLS`` roles always skip RLS, so when the store connects as one (the compose default),
  it switches each pooled connection to :data:`PLANNER_ROLE`, a ``NOLOGIN`` role with no bypass,
  holding only the privileges the store needs.
- The alert job lists workspaces across clients. It reads ``planner_workspace``, a registry of
  workspace ids only, instead of opening the content tables.

The Watch tables (``planner_watch_source``, ``planner_watch_change``) hold public sources and stay
global.
"""

from __future__ import annotations

#: NOLOGIN role the store switches to when its login role would bypass RLS.
PLANNER_ROLE = "complianceos_planner"

#: Transaction-local setting that names the current workspace.
WORKSPACE_SETTING = "app.workspace"

#: Tables filtered directly on their ``workspace`` column.
WORKSPACE_TABLES = (
    "planner_mission",
    "planner_history_checkpoint",
    "planner_usage_event",
    "planner_alert_recipients",
)

#: Tables filtered through a visible parent row: (table, parent table, foreign key column).
CHILD_TABLES = (
    ("planner_application", "planner_mission", "mission_id"),
    ("planner_application_event", "planner_application", "application_id"),
    ("planner_contact", "planner_application", "application_id"),
)

#: Tables the store reads and writes with no workspace filter (public sources; workspace ids).
GLOBAL_TABLES = ("planner_watch_source", "planner_watch_change", "planner_workspace")

_CURRENT = f"current_setting('{WORKSPACE_SETTING}', true)"


def _policy(table: str, using: str) -> str:
    name = f"{table}_workspace_isolation"
    return (
        f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;\n"
        f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;\n"
        f"DROP POLICY IF EXISTS {name} ON {table};\n"
        f"CREATE POLICY {name} ON {table} FOR ALL USING ({using}) WITH CHECK ({using});\n"
    )


def policies_sql() -> str:
    """Idempotent DDL: enable and force RLS, and (re)create one isolation policy per table."""
    parts = [_policy(t, f"workspace = {_CURRENT}") for t in WORKSPACE_TABLES]
    parts += [
        _policy(t, f"EXISTS (SELECT 1 FROM {parent} p WHERE p.id = {t}.{fk})")
        for t, parent, fk in CHILD_TABLES
    ]
    return "".join(parts)


def role_sql() -> str:
    """Idempotent DDL creating :data:`PLANNER_ROLE` and granting exactly what the store needs.

    Run only when the connecting role can create roles (a superuser, in practice). The current
    login role is made a member so it may ``SET ROLE`` to it.
    """
    scoped = [*WORKSPACE_TABLES, *(t for t, _, _ in CHILD_TABLES), *GLOBAL_TABLES]
    tables = ", ".join(scoped)
    return (
        "DO $$ BEGIN\n"
        f"  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{PLANNER_ROLE}') THEN\n"
        f"    CREATE ROLE {PLANNER_ROLE} NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEROLE NOCREATEDB;\n"
        "  END IF;\n"
        "EXCEPTION WHEN duplicate_object THEN NULL;  -- another process created it first\n"
        "END $$;\n"
        f"GRANT {PLANNER_ROLE} TO CURRENT_USER;\n"
        f"GRANT USAGE ON SCHEMA public TO {PLANNER_ROLE};\n"
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON {tables} TO {PLANNER_ROLE};\n"
        f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {PLANNER_ROLE};\n"
    )


#: Whether the connecting role skips RLS (then the store must switch to :data:`PLANNER_ROLE`).
BYPASSES_RLS_SQL = "SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = current_user"

#: Scope the current transaction to one workspace (transaction-local: ``is_local`` = true).
SET_WORKSPACE_SQL = f"SELECT set_config('{WORKSPACE_SETTING}', $1, true)"

SET_ROLE_SQL = f"SET ROLE {PLANNER_ROLE}"

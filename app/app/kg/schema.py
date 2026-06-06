"""L2 relational schema applied by the BFF on KG connect.

Canonical DDL mirrors layers/L2-knowledge-graph/ingest/schema.sql (kept here as a Python
constant so the app applies it without a file copy in the image). The AGE graph + extensions
already exist from cross-cutting/deploy/kg-init/init.sql; AGE labels auto-create on first
Cypher CREATE.
"""

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS obligation_embedding (
    ref_code   TEXT PRIMARY KEY,
    framework  TEXT NOT NULL,
    content    TEXT NOT NULL,
    embedding  vector(384) NOT NULL
);

CREATE TABLE IF NOT EXISTS context_core (
    id          BIGSERIAL PRIMARY KEY,
    draft_id    TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_ref  TEXT NOT NULL,
    derivation  TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS context_core_draft_idx ON context_core (draft_id);
"""

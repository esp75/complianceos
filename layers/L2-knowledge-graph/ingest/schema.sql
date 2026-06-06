-- L2 relational schema, applied idempotently by the BFF on first KG connect.
-- The AGE graph `celestia_kg` and the `age`/`vector` extensions already exist from
-- cross-cutting/deploy/kg-init/init.sql (Phase 1 M6). AGE node/edge labels (Obligation,
-- EvidenceType, CITES, REQUIRES_EVIDENCE) are auto-created on first Cypher CREATE, so they
-- need no DDL here. See layers/L2-knowledge-graph/ontology/RASE-celestia.md.

-- LightRAG local level (ADR-0004): per-obligation embeddings for pgvector ANN.
-- Dim 384 is forward-compatible with BAAI/bge-small / bge-m3 (the production embedding swap).
CREATE TABLE IF NOT EXISTS obligation_embedding (
    ref_code   TEXT PRIMARY KEY,
    framework  TEXT NOT NULL,
    content    TEXT NOT NULL,
    embedding  vector(384) NOT NULL
);

-- Context Cores (ADR-0005): one provenance row per source a draft cites, so every
-- claim/citation is backed by a recorded derivation.
CREATE TABLE IF NOT EXISTS context_core (
    id          BIGSERIAL PRIMARY KEY,
    draft_id    TEXT NOT NULL,
    source_type TEXT NOT NULL,          -- 'obligation' | 'evidence'
    source_ref  TEXT NOT NULL,          -- obligation ref_code or evidence id
    derivation  TEXT NOT NULL,          -- how the source entered the draft
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS context_core_draft_idx ON context_core (draft_id);

-- Celestia KG Postgres bootstrap. Runs against the `kg` database (POSTGRES_DB=kg).
-- Enables both extensions the L2 knowledge graph needs and creates a starter graph,
-- proving AGE + pgvector coexist in one Postgres 17 instance (ADR-0007).
-- Not consumed in Phase 1; L2 (Phase 3) builds on this.

CREATE EXTENSION IF NOT EXISTS age;
CREATE EXTENSION IF NOT EXISTS vector;

LOAD 'age';
SET search_path = ag_catalog, "$user", public;

-- starter graph for L2; idempotent guard so re-init does not error
SELECT create_graph('celestia_kg')
WHERE NOT EXISTS (SELECT 1 FROM ag_catalog.ag_graph WHERE name = 'celestia_kg');

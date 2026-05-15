-- Bootstrap Postgres extensions for complianceOS.
-- Runs once on first container start (Apache AGE image picks up
-- /docker-entrypoint-initdb.d/*.sql).

CREATE EXTENSION IF NOT EXISTS age;
CREATE EXTENSION IF NOT EXISTS vector;
LOAD 'age';
SET search_path = ag_catalog, "$user", public;

-- Reg-graph knowledge graph for citation-forced RAG.
SELECT create_graph('reg_graph');

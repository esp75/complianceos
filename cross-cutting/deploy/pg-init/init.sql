-- Celestia L1 operational Postgres bootstrap.
-- Derived from theopenlane upstream docker/pg-init-scripts/init.sql, minus the
-- `windmill` DB (not used by Celestia). theopenlane's goose migrations own the
-- `core` schema; OpenFGA owns `openfga`; River owns `jobs`.
-- NOTE: Apache AGE + pgvector live in a SEPARATE kg-postgres instance (see M6),
-- never in this migration-managed operational DB.

CREATE DATABASE openfga;
GRANT ALL PRIVILEGES ON DATABASE openfga TO postgres;

CREATE DATABASE core;
GRANT ALL PRIVILEGES ON DATABASE core TO postgres;

CREATE DATABASE jobs;
GRANT ALL PRIVILEGES ON DATABASE jobs TO postgres;

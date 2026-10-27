-- Zitadel keeps its own database and role on the same Postgres instance.
-- Runs once, on first init of the data volume. The password comes from the
-- ZITADEL_DB_PASSWORD env var on the postgres service, never from this file.
\getenv zitadel_pw ZITADEL_DB_PASSWORD
CREATE ROLE zitadel LOGIN PASSWORD :'zitadel_pw';
CREATE DATABASE zitadel OWNER zitadel;
-- Nothing except the zitadel role may connect to its database. The API role
-- (celestia) is the cluster superuser today; see the note in docker-compose.yml.
REVOKE CONNECT ON DATABASE zitadel FROM PUBLIC;
GRANT CONNECT ON DATABASE zitadel TO zitadel;

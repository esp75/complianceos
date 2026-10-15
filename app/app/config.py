"""Application configuration via pydantic-settings.

All settings are overridable by environment variables prefixed ``CELESTIA_``
(e.g. ``CELESTIA_OPENLANE_GRAPHQL_URL``). Inside docker-compose the defaults below
resolve services by their compose service names.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CELESTIA_", env_file=".env")

    # --- L1 substrate (theopenlane/core) ---
    # GraphQL endpoint of the theopenlane Go service. ADR-0012: the only integration boundary.
    openlane_graphql_url: str = "http://core:17608/query"

    # --- Authorization (OpenFGA) ---
    # BFF-boundary authorization checks happen against this OpenFGA HTTP API (ADR-0012).
    openfga_url: str = "http://openfga:8080"
    # theopenlane names its store "openlane"; the client resolves store + latest model id.
    openfga_store_name: str = "openlane"

    # --- OIDC (Dex for local dev; EU IdP in Phase 4) ---
    oidc_issuer_url: str = "http://dex:5556/dex"
    oidc_client_id: str = "local-client"

    # --- L3 SDER engine (Orekit microservice, ADR-0013) ---
    # REST base URL of the Orekit JVM service; resolves by compose service name.
    orekit_base_url: str = "http://orekit:8090"
    # Default reporting threshold for conjunction events (km).
    orekit_conjunction_threshold_km: float = 10.0

    # --- L2 knowledge graph (kg-postgres: Postgres 17 + AGE + pgvector, ADR-0007/0014) ---
    # In-network DSN; the kg-postgres service listens on 5432 (host 5433). Behind the `kg`
    # compose profile — L2/L4 endpoints 503 when it is not running.
    kg_dsn: str = "postgresql://postgres:password@kg-postgres:5432/kg"
    # Directory of the L1 framework YAMLs that L2 ingest reads (ADR-0014). Defaults to the
    # repo path for local dev; the app image sets CELESTIA_FRAMEWORKS_DIR=/srv/frameworks.
    frameworks_dir: str = ""

    # --- L4 LLM (Anthropic EU, ADR-0010) ---
    # When the key is empty, drafting/extraction use deterministic offline paths (no US LLM
    # call). Set CELESTIA_ANTHROPIC_API_KEY (env only, never committed) to wire live Claude.
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-7"
    anthropic_base_url: str = "https://api.anthropic.com"

    # --- Trust layer (Phase 4, ADR-0016) ---
    # Master seed for per-Organization Ed25519 key derivation (HKDF-SHA256, info=org_id). Env-only
    # (CELESTIA_TRUST_SIGNING_SEED), never committed, EU-side. Production target is an EU KMS behind
    # the KeyStore interface. When empty the /bundle/sign endpoint 503s (no signing with a zero key).
    trust_signing_seed: str = ""
    # DSN for the trust store (tamper-evident bundle/audit chain). Defaults to the L2 KG DSN so the
    # trust tables share the same Postgres; set CELESTIA_TRUST_DSN to separate them later.
    trust_dsn: str = ""

    # --- HTTP client tuning ---
    upstream_timeout_seconds: float = 10.0


@lru_cache
def get_settings() -> Settings:
    return Settings()

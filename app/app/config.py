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

    # --- OIDC (Dex for local dev; EU IdP in Phase 4) ---
    oidc_issuer_url: str = "http://dex:5556/dex"
    oidc_client_id: str = "local-client"

    # --- HTTP client tuning ---
    upstream_timeout_seconds: float = 10.0


@lru_cache
def get_settings() -> Settings:
    return Settings()

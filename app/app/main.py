"""Celestia BFF entrypoint.

Wires the theopenlane GraphQL client into app state at startup and mounts routers.
Run with: ``uvicorn app.main:app``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.api import auth, evidence, frameworks, health, kg, organizations, portal, sder
from app.clients.kg import KGClient
from app.clients.openfga import OpenFGAClient
from app.clients.openlane import OpenlaneClient
from app.clients.orekit import OrekitClient
from app.config import get_settings
from app.kg.embeddings import HashingEmbedding
from app.kg.schema import SCHEMA_SQL
from app.llm.anthropic_eu import AnthropicEUClient


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=settings.upstream_timeout_seconds) as http:
        app.state.openlane = OpenlaneClient(settings, http)
        app.state.openfga = OpenFGAClient(settings, http)
        # L3 SDER engine — same shared transport (one httpx client, ADR-0013).
        app.state.orekit = OrekitClient(settings, http)
        # L2 knowledge graph (kg-postgres). Behind the `kg` compose profile, so connect
        # tolerantly — L2/L4 endpoints 503 when it is unreachable (ADR-0014).
        app.state.kg = KGClient(settings.kg_dsn)
        try:
            await app.state.kg.connect()
            await app.state.kg.apply_schema(SCHEMA_SQL)
        except Exception:  # noqa: BLE001 - kg is optional; never block app startup
            pass
        # L2 embedding provider (deterministic v0; bge-m3 swap behind the interface).
        app.state.embed = HashingEmbedding()
        # L4 LLM provider (ADR-0010). No key -> None; callers use deterministic offline paths.
        app.state.llm = (
            AnthropicEUClient(settings.anthropic_api_key, settings.anthropic_model, http,
                              base_url=settings.anthropic_base_url)
            if settings.anthropic_api_key
            else None
        )
        try:
            yield
        finally:
            await app.state.kg.close()


app = FastAPI(
    title="Celestia ComplianceOS API",
    version="0.2.0",
    summary="BFF / orchestration over the theopenlane L1 substrate",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(organizations.router)
app.include_router(frameworks.router)
app.include_router(evidence.router)
app.include_router(sder.router)
app.include_router(kg.router)
app.include_router(portal.router)

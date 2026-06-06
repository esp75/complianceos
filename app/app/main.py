"""Celestia BFF entrypoint.

Wires the theopenlane GraphQL client into app state at startup and mounts routers.
Run with: ``uvicorn app.main:app``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.api import auth, evidence, frameworks, health, organizations, portal, sder
from app.clients.kg import KGClient
from app.clients.openfga import OpenFGAClient
from app.clients.openlane import OpenlaneClient
from app.clients.orekit import OrekitClient
from app.config import get_settings
from app.kg.schema import SCHEMA_SQL


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
app.include_router(portal.router)

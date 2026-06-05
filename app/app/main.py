"""Celestia BFF entrypoint.

Wires the theopenlane GraphQL client into app state at startup and mounts routers.
Run with: ``uvicorn app.main:app``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.api import auth, health
from app.clients.openfga import OpenFGAClient
from app.clients.openlane import OpenlaneClient
from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=settings.upstream_timeout_seconds) as http:
        app.state.openlane = OpenlaneClient(settings, http)
        app.state.openfga = OpenFGAClient(settings, http)
        yield


app = FastAPI(
    title="Celestia ComplianceOS API",
    version="0.2.0",
    summary="BFF / orchestration over the theopenlane L1 substrate",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(auth.router)

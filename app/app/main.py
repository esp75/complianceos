"""Celestia BFF entrypoint.

Wires the theopenlane GraphQL client into app state at startup and mounts routers.
Run with: ``uvicorn app.main:app``.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.api import (
    auth,
    compliance,
    draft,
    evidence,
    frameworks,
    health,
    kg,
    organizations,
    planner,
    portal,
    sder,
)
from app.api.bundle import sign as bundle_sign
from app.api.bundle.sign_pdf import DetachedEd25519PdfSigner
from app.api.trust.keystore import DerivedKeyStore
from app.api.trust.store import TrustStore
from app.clients.kg import KGClient
from app.clients.openfga import OpenFGAClient
from app.clients.openlane import OpenlaneClient
from app.clients.orekit import OrekitClient
from app.config import get_settings
from app.kg.embeddings import HashingEmbedding
from app.kg.schema import SCHEMA_SQL
from app.llm.anthropic_eu import AnthropicEUClient
from app.planner.knowledge import KnowledgeError, load_knowledge
from app.planner.store import MemoryPlannerStore, PlannerStore, PostgresPlannerStore

log = logging.getLogger("celestia.api")


async def _planner_store(dsn: str) -> PlannerStore:
    """Postgres when reachable; otherwise process memory, so the planner always starts."""
    store = PostgresPlannerStore(dsn)
    try:
        await store.connect()
        await store.apply_schema()
        return store
    except Exception:  # noqa: BLE001 - any connection failure falls back to memory
        await store.close()
        log.warning("planner: Postgres unreachable at startup; using an in-memory store "
                    "(data is lost on restart)")
        return MemoryPlannerStore()


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
        # Trust layer (Phase 4, ADR-0016). Shares the kg-postgres unless CELESTIA_TRUST_DSN is set;
        # connect tolerantly so the app starts without it — /bundle/sign 503s via require_trust.
        app.state.trust = TrustStore(settings.trust_dsn or settings.kg_dsn)
        try:
            await app.state.trust.connect()
            await app.state.trust.apply_schema()
        except Exception:  # noqa: BLE001 - trust store is optional; never block app startup
            pass
        app.state.trust_keystore = DerivedKeyStore(settings.trust_signing_seed.encode("utf-8"))
        app.state.bundle_signer = DetachedEd25519PdfSigner()
        # Regulatory path planner (ADR-0018): the open knowledge pack + mission/application store.
        try:
            app.state.knowledge = load_knowledge()
        except KnowledgeError as exc:
            app.state.knowledge = None
            log.error("planner: knowledge pack invalid:\n%s", exc)
        app.state.planner_store = await _planner_store(settings.planner_dsn or settings.kg_dsn)
        try:
            yield
        finally:
            await app.state.kg.close()
            await app.state.trust.close()
            if isinstance(app.state.planner_store, PostgresPlannerStore):
                await app.state.planner_store.close()


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
app.include_router(compliance.router)
app.include_router(kg.router)
app.include_router(draft.router)
app.include_router(planner.router)
app.include_router(portal.router)
app.include_router(bundle_sign.router)

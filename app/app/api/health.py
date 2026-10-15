"""Liveness and readiness endpoints.

- ``/healthz`` — liveness: the process is up. Never touches upstreams.
- ``/readyz``  — readiness. In team mode (``CELESTIA_AUTH_MODE=openlane``) the BFF must reach
  theopenlane's GraphQL, or it returns 503 (the M1 proof that the BFF -> L1 wire is connected).
  In local mode (the default, ADR-0018) theopenlane is optional and readiness depends on the
  planner: its knowledge pack must have loaded. Orekit, the KG and the planner store kind are
  reported informationally.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response, status

from app.clients.openlane import OpenlaneClient, OpenlaneError
from app.clients.orekit import OrekitClient, OrekitError
from app.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(request: Request, response: Response) -> dict[str, object]:
    client: OpenlaneClient = request.app.state.openlane
    try:
        reachable = await client.ping()
    except OpenlaneError:
        reachable = False

    # Informational only — orekit/kg being down must not fail BFF readiness (both are
    # behind optional compose profiles).
    orekit: OrekitClient = request.app.state.orekit
    try:
        orekit_ready = await orekit.ping()
    except OrekitError:
        orekit_ready = False

    kg_ready = await request.app.state.kg.ping()
    store = getattr(request.app.state, "planner_store", None)
    planner = {
        "knowledge": getattr(request.app.state, "knowledge", None) is not None,
        "store": getattr(store, "kind", None),
    }
    body: dict[str, object] = {"openlane": reachable, "orekit": orekit_ready, "kg": kg_ready,
                               "planner": planner, "mode": get_settings().auth_mode}

    needed = planner["knowledge"] if get_settings().auth_mode == "local" else reachable
    if not needed:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unavailable", **body}
    return {"status": "ready", **body}

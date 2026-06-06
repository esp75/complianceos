"""Liveness and readiness endpoints.

- ``/healthz`` — liveness: the process is up. Never touches upstreams.
- ``/readyz``  — readiness: the BFF can reach theopenlane's GraphQL. Returns 503
  otherwise. This is the M1 proof that the BFF -> L1 wire is connected. The L3 Orekit
  probe is reported informationally and does NOT gate readiness (Phase-1 behavior is
  unchanged; the SDER service is optional, behind the compose ``sder`` profile).
"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response, status

from app.clients.openlane import OpenlaneClient, OpenlaneError
from app.clients.orekit import OrekitClient, OrekitError

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

    # Informational only — orekit being down must not fail BFF readiness.
    orekit: OrekitClient = request.app.state.orekit
    try:
        orekit_ready = await orekit.ping()
    except OrekitError:
        orekit_ready = False

    if not reachable:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unavailable", "openlane": False, "orekit": orekit_ready}

    return {"status": "ready", "openlane": True, "orekit": orekit_ready}

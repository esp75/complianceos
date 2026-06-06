"""M1 health-endpoint tests. No live theopenlane required: the openlane client's
ping is stubbed so /readyz logic is verified in isolation.
"""

from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI

from app.api import health


class _StubPingable:
    def __init__(self, *, reachable: bool) -> None:
        self._reachable = reachable

    async def ping(self) -> bool:
        return self._reachable


def _make_app(*, reachable: bool, orekit_ready: bool = True) -> FastAPI:
    app = FastAPI()
    app.state.openlane = _StubPingable(reachable=reachable)
    app.state.orekit = _StubPingable(reachable=orekit_ready)
    app.include_router(health.router)
    return app


@pytest.mark.asyncio
async def test_healthz_is_ok_without_upstream() -> None:
    app = _make_app(reachable=False)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_readyz_ok_when_openlane_reachable() -> None:
    app = _make_app(reachable=True, orekit_ready=True)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/readyz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ready", "openlane": True, "orekit": True}


@pytest.mark.asyncio
async def test_readyz_503_when_openlane_unreachable() -> None:
    app = _make_app(reachable=False, orekit_ready=False)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/readyz")
    assert resp.status_code == 503
    assert resp.json() == {"status": "unavailable", "openlane": False, "orekit": False}

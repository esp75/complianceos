"""M1 health-endpoint tests. No live theopenlane required: the openlane client's
ping is stubbed so /readyz logic is verified in isolation.
"""

from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI

from app.api import health


class _StubOpenlane:
    def __init__(self, *, reachable: bool) -> None:
        self._reachable = reachable

    async def ping(self) -> bool:
        return self._reachable


def _make_app(*, reachable: bool) -> FastAPI:
    app = FastAPI()
    app.state.openlane = _StubOpenlane(reachable=reachable)
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
    app = _make_app(reachable=True)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/readyz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ready", "openlane": True}


@pytest.mark.asyncio
async def test_readyz_503_when_openlane_unreachable() -> None:
    app = _make_app(reachable=False)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/readyz")
    assert resp.status_code == 503
    assert resp.json() == {"status": "unavailable", "openlane": False}

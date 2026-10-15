"""M1 health-endpoint tests. No live theopenlane required: the openlane client's
ping is stubbed so /readyz logic is verified in isolation.
"""

from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI

from app.api import health
from app.config import get_settings


@pytest.fixture
def mode(monkeypatch: pytest.MonkeyPatch):  # noqa: ANN201
    """Set CELESTIA_AUTH_MODE for one test (settings are cached)."""
    def _set(value: str) -> None:
        monkeypatch.setenv("CELESTIA_AUTH_MODE", value)
        get_settings.cache_clear()
    yield _set
    get_settings.cache_clear()


class _StubPingable:
    def __init__(self, *, reachable: bool) -> None:
        self._reachable = reachable

    async def ping(self) -> bool:
        return self._reachable


class _Store:
    kind = "memory"


def _make_app(*, reachable: bool, orekit_ready: bool = True, kg_ready: bool = True,
              knowledge: object | None = object()) -> FastAPI:
    app = FastAPI()
    app.state.openlane = _StubPingable(reachable=reachable)
    app.state.orekit = _StubPingable(reachable=orekit_ready)
    app.state.kg = _StubPingable(reachable=kg_ready)
    app.state.knowledge = knowledge
    app.state.planner_store = _Store()
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


async def _readyz(app: FastAPI) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get("/readyz")


@pytest.mark.asyncio
async def test_team_mode_ready_when_openlane_reachable(mode) -> None:  # noqa: ANN001
    mode("openlane")
    resp = await _readyz(_make_app(reachable=True, orekit_ready=True))
    assert resp.status_code == 200
    body = resp.json()
    assert (body["status"], body["openlane"], body["orekit"], body["kg"]) == ("ready", True, True, True)


@pytest.mark.asyncio
async def test_team_mode_503_when_openlane_unreachable(mode) -> None:  # noqa: ANN001
    mode("openlane")
    resp = await _readyz(_make_app(reachable=False, orekit_ready=False, kg_ready=False))
    assert resp.status_code == 503
    body = resp.json()
    assert (body["status"], body["openlane"], body["orekit"], body["kg"]) == (
        "unavailable", False, False, False)


@pytest.mark.asyncio
async def test_local_mode_ready_without_openlane(mode) -> None:  # noqa: ANN001
    mode("local")
    resp = await _readyz(_make_app(reachable=False))
    assert resp.status_code == 200
    assert resp.json()["planner"] == {"knowledge": True, "store": "memory"}


@pytest.mark.asyncio
async def test_local_mode_503_when_knowledge_failed(mode) -> None:  # noqa: ANN001
    mode("local")
    resp = await _readyz(_make_app(reachable=True, knowledge=None))
    assert resp.status_code == 503

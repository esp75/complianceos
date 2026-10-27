from __future__ import annotations

import os
from collections.abc import AsyncIterator

import httpx
import pytest

from app.api.main import app


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    # Lifespan does not run under ASGITransport, so DATABASE_URL is never read here.
    app.state.pool = None
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_health_is_ok(client: httpx.AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_obligations_503_without_database(client: httpx.AsyncClient) -> None:
    resp = await client.get("/obligations")
    assert resp.status_code == 503


async def test_obligations_rejects_bad_limit_before_querying(
    client: httpx.AsyncClient,
) -> None:
    # A non-None sentinel pool gets past the 503 check. The request then fails
    # validation before pool.acquire() is ever called, so the sentinel is never used.
    app.state.pool = object()
    resp = await client.get("/obligations", params={"limit": 0})
    assert resp.status_code == 422
    resp = await client.get("/obligations", params={"offset": -1})
    assert resp.status_code == 422


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="needs DATABASE_URL")
async def test_obligations_empty_list_against_real_db() -> None:
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as c:
            resp = await c.get("/obligations")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []

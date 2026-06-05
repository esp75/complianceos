"""M2 auth-router tests. theopenlane and OpenFGA are stubbed so the BFF's
authn seam (/auth/me) and authz boundary (/auth/can) are tested in isolation.
"""

from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI

from app.api import auth


class _StubOpenlane:
    def __init__(self, user: dict | None) -> None:
        self._user = user or {}

    async def get_self(self, token: str) -> dict:
        # A made-up token resolves to nothing (simulates an invalid/unauthorized token).
        return self._user if token == "good" else {}


class _StubOpenFGA:
    def __init__(self, allowed: bool) -> None:
        self._allowed = allowed

    async def check(self, user: str, relation: str, obj: str, *, context=None) -> bool:
        return self._allowed


def _client(*, user: dict | None, allowed: bool = True) -> httpx.AsyncClient:
    app = FastAPI()
    app.state.openlane = _StubOpenlane(user)
    app.state.openfga = _StubOpenFGA(allowed)
    app.include_router(auth.router)
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


@pytest.mark.asyncio
async def test_me_requires_bearer() -> None:
    async with _client(user={"id": "01X", "email": "a@b.c"}) as c:
        assert (await c.get("/auth/me")).status_code == 401


@pytest.mark.asyncio
async def test_me_rejects_unknown_token() -> None:
    async with _client(user={"id": "01X"}) as c:
        r = await c.get("/auth/me", headers={"Authorization": "Bearer bad"})
        assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_user_and_hides_token() -> None:
    async with _client(user={"id": "01X", "email": "a@b.c"}) as c:
        r = await c.get("/auth/me", headers={"Authorization": "Bearer good"})
        assert r.status_code == 200
        body = r.json()
        assert body == {"id": "01X", "email": "a@b.c"}
        assert "_token" not in body


@pytest.mark.asyncio
async def test_can_returns_fga_decision() -> None:
    async with _client(user={"id": "01X"}, allowed=False) as c:
        r = await c.get(
            "/auth/can",
            params={"relation": "can_create_evidence", "object": "organization:01O"},
            headers={"Authorization": "Bearer good"},
        )
        assert r.status_code == 200
        assert r.json() == {
            "user": "user:01X",
            "relation": "can_create_evidence",
            "object": "organization:01O",
            "allowed": False,
        }

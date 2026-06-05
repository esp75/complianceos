"""Unit tests for the OpenFGA client: store/model resolution + check parsing,
using an httpx MockTransport (no live OpenFGA needed).
"""

from __future__ import annotations

import httpx
import pytest

from app.clients.openfga import OpenFGAClient, OpenFGAError
from app.config import Settings

STORE_ID = "01STORE"
MODEL_ID = "01MODEL"


def _handler(check_allowed: bool):
    def handle(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/stores":
            return httpx.Response(200, json={"stores": [{"id": STORE_ID, "name": "openlane"}]})
        if path.endswith("/authorization-models"):
            return httpx.Response(200, json={"authorization_models": [{"id": MODEL_ID}]})
        if path.endswith("/check"):
            return httpx.Response(200, json={"allowed": check_allowed})
        return httpx.Response(404)

    return handle


def _client(allowed: bool) -> OpenFGAClient:
    http = httpx.AsyncClient(transport=httpx.MockTransport(_handler(allowed)))
    return OpenFGAClient(Settings(openfga_url="http://fga"), http)


@pytest.mark.asyncio
async def test_resolve_discovers_store_and_model() -> None:
    fga = _client(True)
    await fga.resolve()
    assert fga._store_id == STORE_ID
    assert fga._model_id == MODEL_ID


@pytest.mark.asyncio
async def test_check_allowed_true() -> None:
    fga = _client(True)
    assert await fga.check("user:01U", "can_create_evidence", "organization:01O") is True


@pytest.mark.asyncio
async def test_check_allowed_false() -> None:
    fga = _client(False)
    assert await fga.check("user:01U", "can_create_evidence", "organization:01O") is False


@pytest.mark.asyncio
async def test_missing_store_raises() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"stores": []})

    http = httpx.AsyncClient(transport=httpx.MockTransport(handle))
    fga = OpenFGAClient(Settings(openfga_url="http://fga"), http)
    with pytest.raises(OpenFGAError):
        await fga.resolve()

"""Unit tests for OrekitClient — fully stubbed via httpx.MockTransport, no live JVM."""

from __future__ import annotations

import httpx
import pytest

from app.clients.orekit import OrekitClient, OrekitError
from app.config import Settings

ISS_TLE = {"line1": "1 25544U ...", "line2": "2 25544 ..."}


def _client(handler: object) -> tuple[OrekitClient, httpx.AsyncClient]:
    transport = httpx.MockTransport(handler)  # type: ignore[arg-type]
    http = httpx.AsyncClient(transport=transport, base_url="http://orekit:8090")
    return OrekitClient(Settings(), http), http


@pytest.mark.asyncio
async def test_propagate_parses_state_vector() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/propagate"
        return httpx.Response(
            200, json={"position": [6780.0, 0.0, 0.0], "velocity": [0.0, 7.5, 0.0], "frame": "TEME", "epoch": "x"}
        )

    client, http = _client(handler)
    async with http:
        resp = await client.propagate(ISS_TLE, "2008-09-20T12:25:40Z")
        assert resp["position"][0] == 6780.0
        assert resp["frame"] == "TEME"


@pytest.mark.asyncio
async def test_conjunction_parses_and_passes_threshold() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        seen.update(json.loads(request.content))
        return httpx.Response(200, json={"events": [], "minMissDistanceKm": 4.2})

    client, http = _client(handler)
    async with http:
        window = {"start": "a", "end": "b", "stepSeconds": 60}
        resp = await client.conjunction(ISS_TLE, ISS_TLE, window, threshold_km=5.0)
        assert resp["minMissDistanceKm"] == 4.2
        assert seen["thresholdKm"] == 5.0


@pytest.mark.asyncio
async def test_error_envelope_surfaces_code_and_message() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": {"code": "invalid_tle", "message": "malformed TLE"}})

    client, http = _client(handler)
    async with http:
        with pytest.raises(OrekitError, match="invalid_tle: malformed TLE"):
            await client.propagate(ISS_TLE, "epoch")


@pytest.mark.asyncio
async def test_server_error_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": {"code": "internal", "message": "boom"}})

    client, http = _client(handler)
    async with http:
        with pytest.raises(OrekitError, match="500"):
            await client.propagate(ISS_TLE, "epoch")


@pytest.mark.asyncio
async def test_transport_error_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    client, http = _client(handler)
    async with http:
        with pytest.raises(OrekitError, match="request failed"):
            await client.propagate(ISS_TLE, "epoch")


@pytest.mark.asyncio
async def test_ping_reflects_readyz_status() -> None:
    def ready(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "ready"})

    def not_ready(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": {"code": "not_ready", "message": "no data"}})

    client, http = _client(ready)
    async with http:
        assert await client.ping() is True

    client, http = _client(not_ready)
    async with http:
        assert await client.ping() is False

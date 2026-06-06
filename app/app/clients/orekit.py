"""Typed async client to the L3 Orekit microservice (REST/JSON, ADR-0013).

Mirrors the openlane/openfga client pattern: a thin typed wrapper over the shared
``httpx.AsyncClient``. The SDER router depends on this client, never on raw HTTP. The
Orekit service is reached over the cluster-internal network only (ADR-0002).
"""

from __future__ import annotations

from typing import Any, cast

import httpx

from app.config import Settings


class OrekitError(RuntimeError):
    """Raised on a transport error or a CONTRACT.md error envelope from the service."""


class OrekitClient:
    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self._base = settings.orekit_base_url.rstrip("/")
        self._http = client

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            resp = await self._http.post(f"{self._base}{path}", json=payload)
        except httpx.HTTPError as exc:
            raise OrekitError(f"orekit request failed: {exc}") from exc
        if resp.status_code >= 400:
            raise OrekitError(f"orekit {path} -> {resp.status_code}: {self._error_detail(resp)}")
        return cast("dict[str, Any]", resp.json())

    @staticmethod
    def _error_detail(resp: httpx.Response) -> str:
        """Surface the {"error":{"code","message"}} envelope when present."""
        try:
            body = resp.json()
        except ValueError:
            return resp.text or resp.reason_phrase
        err = body.get("error") if isinstance(body, dict) else None
        if isinstance(err, dict):
            return f"{err.get('code')}: {err.get('message')}"
        return str(body)

    async def propagate(self, tle: dict[str, str], epoch: str) -> dict[str, Any]:
        """Propagate a TLE to ``epoch``; returns position/velocity (km, km/s) in TEME."""
        return await self._post("/propagate", {"tle": tle, "epoch": epoch})

    async def conjunction(
        self,
        tle1: dict[str, str],
        tle2: dict[str, str],
        window: dict[str, Any],
        *,
        threshold_km: float | None = None,
    ) -> dict[str, Any]:
        """Sampled min-miss-distance screening over ``window`` (start/end/stepSeconds)."""
        payload: dict[str, Any] = {"tle1": tle1, "tle2": tle2, "window": window}
        if threshold_km is not None:
            payload["thresholdKm"] = threshold_km
        return await self._post("/conjunction", payload)

    async def frame_convert(
        self, state: dict[str, Any], from_frame: str, to_frame: str
    ) -> dict[str, Any]:
        """Convert a state vector between reference frames."""
        return await self._post(
            "/frame_convert", {"state": state, "fromFrame": from_frame, "toFrame": to_frame}
        )

    async def ping(self) -> bool:
        """Readiness probe — hits the service's /readyz (200 only once orekit-data is loaded)."""
        try:
            resp = await self._http.get(f"{self._base}/readyz")
        except httpx.HTTPError as exc:
            raise OrekitError(f"orekit readiness check failed: {exc}") from exc
        return resp.status_code == 200

"""Typed async client to the theopenlane/core GraphQL API.

ADR-0012: this is the single integration boundary with the L1 substrate. Domain
routers depend on this client, never on raw GraphQL strings. Keeping all upstream
GraphQL here localizes schema drift across theopenlane SHA bumps.
"""

from __future__ import annotations

from typing import Any, cast

import httpx

from app.config import Settings


class OpenlaneError(RuntimeError):
    """Raised when theopenlane returns a transport error or GraphQL ``errors``."""


class OpenlaneClient:
    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self._url = settings.openlane_graphql_url
        # theopenlane's purpose-built readiness endpoint lives on the same HTTP server
        # as /query (internal/httpserve/route/base.go -> "/ready"). Derive it from the
        # GraphQL URL so a single config value drives both.
        self._ready_url = self._url.rsplit("/", 1)[0] + "/ready"
        self._http = client

    async def execute(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        *,
        token: str | None = None,
    ) -> dict[str, Any]:
        """Run a GraphQL operation and return the ``data`` object.

        When ``token`` is supplied it is forwarded as a bearer credential so
        theopenlane's native OpenFGA checks apply (defense in depth, ADR-0012).
        """
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        try:
            resp = await self._http.post(
                self._url,
                json={"query": query, "variables": variables or {}},
                headers=headers,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:  # transport / status error
            raise OpenlaneError(f"theopenlane request failed: {exc}") from exc

        payload = resp.json()
        if payload.get("errors"):
            raise OpenlaneError(f"theopenlane GraphQL errors: {payload['errors']}")
        return cast("dict[str, Any]", payload.get("data", {}))

    async def get_self(self, token: str) -> dict[str, Any]:
        """Resolve the current user (theopenlane ``self`` query) for a bearer token.

        A Personal Access Token works standalone; a raw JWT also needs core's session
        cookie, which the BFF does not hold — so PATs are the practical BFF credential.
        """
        data = await self.execute("{ self { id email firstName lastName } }", token=token)
        return cast("dict[str, Any]", data.get("self", {}))

    async def ping(self) -> bool:
        """Readiness probe — hits theopenlane's own /ready endpoint.

        ADR-0012 keeps GraphQL as the *data* boundary; readiness is an operational
        signal, so we use core's unauthenticated /ready (which also verifies core's DB)
        on the same HTTP server that serves /query. Returns True on HTTP 200. Used by /readyz.
        """
        try:
            resp = await self._http.get(self._ready_url)
        except httpx.HTTPError as exc:
            raise OpenlaneError(f"theopenlane readiness check failed: {exc}") from exc
        return resp.status_code == 200

"""Async OpenFGA client for BFF-boundary authorization checks.

ADR-0012: the BFF is the authorization enforcement point for everything theopenlane's
embedded model can't express (cross-org insurer/regulator scoping). theopenlane owns
the FGA store; we resolve its store id + latest authorization model and issue checks
against the same store, so our decisions stay consistent with core's.

User/object ids use theopenlane's format: ``user:<ULID>``, ``organization:<ULID>``,
``group:<ULID>``. Group-set refs look like ``group:<ULID>#member``.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.config import Settings


class OpenFGAError(RuntimeError):
    """Raised on transport errors or unexpected OpenFGA responses."""


class OpenFGAClient:
    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self._base = settings.openfga_url.rstrip("/")
        self._store_name = settings.openfga_store_name
        self._http = client
        self._store_id: str | None = None
        self._model_id: str | None = None

    async def resolve(self) -> None:
        """Discover and cache the store id + latest authorization model id.

        Idempotent: a second call is a no-op once both ids are known.
        """
        if self._store_id and self._model_id:
            return
        try:
            stores = (await self._http.get(f"{self._base}/stores")).json().get("stores", [])
        except httpx.HTTPError as exc:
            raise OpenFGAError(f"OpenFGA /stores failed: {exc}") from exc
        store = next((s for s in stores if s.get("name") == self._store_name), None)
        if store is None:
            raise OpenFGAError(f"OpenFGA store {self._store_name!r} not found")
        self._store_id = store["id"]

        try:
            models = (
                await self._http.get(
                    f"{self._base}/stores/{self._store_id}/authorization-models",
                    params={"page_size": 1},
                )
            ).json().get("authorization_models", [])
        except httpx.HTTPError as exc:
            raise OpenFGAError(f"OpenFGA authorization-models failed: {exc}") from exc
        if not models:
            raise OpenFGAError("OpenFGA store has no authorization model")
        self._model_id = models[0]["id"]

    async def check(
        self,
        user: str,
        relation: str,
        obj: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """Return whether ``user`` has ``relation`` on ``obj`` (e.g.
        check("user:01...", "can_create_evidence", "organization:01...")).
        """
        await self.resolve()
        tuple_key = {"user": user, "relation": relation, "object": obj}
        body: dict[str, Any] = {
            "authorization_model_id": self._model_id,
            "tuple_key": tuple_key,
        }
        if context is not None:
            body["context"] = context
        try:
            resp = await self._http.post(
                f"{self._base}/stores/{self._store_id}/check", json=body
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise OpenFGAError(f"OpenFGA check failed: {exc}") from exc
        return bool(resp.json().get("allowed", False))

    async def write_tuple(
        self,
        user: str,
        relation: str,
        obj: str,
        *,
        condition: dict[str, Any] | None = None,
    ) -> None:
        """Write a single relationship tuple. Used by the tetrad seeder for grants
        theopenlane has no mutation for (e.g. a regulator's ``audit_log_viewer``).
        Idempotent against an already-present identical tuple.
        """
        await self.resolve()
        key: dict[str, Any] = {"user": user, "relation": relation, "object": obj}
        if condition is not None:
            key["condition"] = condition
        body = {
            "authorization_model_id": self._model_id,
            "writes": {"tuple_keys": [key]},
        }
        try:
            resp = await self._http.post(
                f"{self._base}/stores/{self._store_id}/write", json=body
            )
        except httpx.HTTPError as exc:
            raise OpenFGAError(f"OpenFGA write failed: {exc}") from exc
        # 400 with "already exists" is benign for idempotent seeding.
        if resp.status_code == 400 and "already exists" in resp.text:
            return
        if resp.status_code >= 400:
            raise OpenFGAError(f"OpenFGA write failed [{resp.status_code}]: {resp.text}")

"""M4 domain-endpoint tests: the BFF-boundary FGA checks gate create/list/history.
theopenlane and OpenFGA are stubbed; we assert the authorization decisions, not upstream.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.api import evidence, frameworks


class StubOpenlane:
    async def get_self(self, token: str) -> dict[str, Any]:
        return {"id": "01U", "email": "u@celestia.eu"} if token == "good" else {}

    async def execute(self, query: str, variables: dict | None = None, *, token: str | None = None) -> dict[str, Any]:
        if "createEvidence" in query:
            return {"createEvidence": {"evidence": {"id": "01E", "displayID": "EV-1", "name": "TLE record"}}}
        if "evidences(where" in query:
            return {"evidences": {"edges": [
                {"node": {"id": "01E", "displayID": "EV-1", "name": "x", "status": "READY"}},
            ]}}
        if "evidence(id" in query:
            return {"evidence": {"id": "01E", "displayID": "EV-1", "name": "x", "status": "READY",
                                 "createdAt": "t0", "updatedAt": "t1", "createdBy": "01U", "updatedBy": "01U",
                                 "owner": {"id": "01O"}}}
        if "standards" in query:
            node = {"id": "01S", "shortName": "EU-SA", "framework": "v1",
                    "controls": {"totalCount": 1, "edges": [{"node": {"refCode": "Art.1", "title": "Scope"}}]}}
            return {"standards": {"edges": [{"node": node}]}}
        return {}


class StubOpenFGA:
    def __init__(self, allow: dict[str, bool]) -> None:
        self._allow = allow

    async def check(self, user: str, relation: str, obj: str, *, context: dict | None = None) -> bool:
        return self._allow.get(relation, False)


def _client(allow: dict[str, bool]) -> httpx.AsyncClient:
    app = FastAPI()
    app.state.openlane = StubOpenlane()
    app.state.openfga = StubOpenFGA(allow)
    app.include_router(evidence.router)
    app.include_router(frameworks.router)
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


AUTH = {"Authorization": "Bearer good"}


@pytest.mark.asyncio
async def test_operator_can_create_evidence() -> None:
    async with _client({"can_create_evidence": True}) as c:
        r = await c.post("/evidence", json={"org_id": "01O", "name": "TLE record"}, headers=AUTH)
        assert r.status_code == 201
        assert r.json()["displayID"] == "EV-1"


@pytest.mark.asyncio
async def test_insurer_blocked_from_create_at_bff() -> None:
    async with _client({"can_create_evidence": False, "can_view": True}) as c:
        r = await c.post("/evidence", json={"org_id": "01O", "name": "x"}, headers=AUTH)
        assert r.status_code == 403
        assert "can_create_evidence" in r.json()["detail"]


@pytest.mark.asyncio
async def test_member_can_list_evidence() -> None:
    async with _client({"can_view": True}) as c:
        r = await c.get("/evidence", params={"org_id": "01O"}, headers=AUTH)
        assert r.status_code == 200
        assert r.json()[0]["displayID"] == "EV-1"


@pytest.mark.asyncio
async def test_history_requires_audit_log_viewer() -> None:
    async with _client({"audit_log_viewer": False}) as c:
        r = await c.get("/evidence/01E/history", headers=AUTH)
        assert r.status_code == 403
    async with _client({"audit_log_viewer": True}) as c:
        r = await c.get("/evidence/01E/history", headers=AUTH)
        assert r.status_code == 200
        assert r.json()["audit"]["createdBy"] == "01U"


@pytest.mark.asyncio
async def test_frameworks_list() -> None:
    async with _client({}) as c:
        r = await c.get("/frameworks", headers=AUTH)
        assert r.status_code == 200
        assert r.json()[0]["shortName"] == "EU-SA"

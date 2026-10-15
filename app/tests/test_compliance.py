"""Compliance-status rollup tests (ADR-0015): the pure rollup classification and the
BFF endpoint's ``can_view`` gate + Standards×Evidence join. theopenlane and OpenFGA are
stubbed; no network needed.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.api import compliance
from app.l5.rollup import COMPLIANT, NOT_ASSESSED, PARTIAL, rollup_status

# --- pure rollup ----------------------------------------------------------------------

_FRAMEWORKS = [
    {"shortName": "ISO-24113", "framework": "2023", "controls": [
        {"refCode": "ISO 24113 §6.4", "title": "Collision avoidance"},
        {"refCode": "ISO 24113 §6.2", "title": "Disposal"},
    ]},
    {"shortName": "EU-SA", "framework": "v1", "controls": [
        {"refCode": "EU-SA Art.3", "title": "Authorisation"},
    ]},
]


def test_rollup_classifies_compliant_partial_and_not_assessed() -> None:
    evidence = [
        {"id": "1", "displayID": "EV-1", "name": "conj", "status": "READY",
         "controlRefs": ["ISO 24113 §6.4"]},          # accepted -> compliant
        {"id": "2", "displayID": "EV-2", "name": "draft disposal", "status": "DRAFT",
         "controlRefs": ["ISO 24113 §6.2"]},           # linked, not accepted -> partial
        # EU-SA Art.3 has no evidence -> not_assessed
    ]
    out = rollup_status(_FRAMEWORKS, evidence)

    iso = next(f for f in out["frameworks"] if f["shortName"] == "ISO-24113")
    statuses = {c["refCode"]: c["status"] for c in iso["controls"]}
    assert statuses["ISO 24113 §6.4"] == COMPLIANT
    assert statuses["ISO 24113 §6.2"] == PARTIAL

    eu = next(f for f in out["frameworks"] if f["shortName"] == "EU-SA")
    assert eu["controls"][0]["status"] == NOT_ASSESSED

    assert out["summary"] == {
        COMPLIANT: 1, PARTIAL: 1, NOT_ASSESSED: 1, "total": 3, "percentCompliant": 33.3,
    }


def test_rollup_attaches_linked_evidence_to_its_control() -> None:
    evidence = [{"id": "9", "displayID": "EV-9", "name": "conj", "status": "READY",
                 "controlRefs": ["ISO 24113 §6.4"]}]
    out = rollup_status(_FRAMEWORKS, evidence)
    ctrl = out["frameworks"][0]["controls"][0]
    assert ctrl["evidenceCount"] == 1
    assert ctrl["evidence"][0]["displayID"] == "EV-9"


def test_rollup_empty_org_is_all_not_assessed() -> None:
    out = rollup_status(_FRAMEWORKS, [])
    assert out["summary"][NOT_ASSESSED] == 3
    assert out["summary"]["percentCompliant"] == 0.0


def test_rollup_one_evidence_covering_two_controls() -> None:
    evidence = [{"id": "1", "displayID": "EV-1", "name": "x", "status": "approved",
                 "controlRefs": ["ISO 24113 §6.4", "EU-SA Art.3"]}]
    out = rollup_status(_FRAMEWORKS, evidence)
    assert out["summary"][COMPLIANT] == 2


# --- endpoint -------------------------------------------------------------------------


class StubOpenlane:
    async def get_self(self, token: str) -> dict[str, Any]:
        return {"id": "01U", "email": "u@celestia.eu"} if token == "good" else {}

    async def execute(
        self, query: str, variables: dict | None = None, *, token: str | None = None
    ) -> dict[str, Any]:
        if "standards" in query:
            return {"standards": {"edges": [
                {"node": {"id": "01S", "shortName": "ISO-24113", "framework": "2023", "controls": {
                    "edges": [
                        {"node": {"refCode": "ISO 24113 §6.4", "title": "Collision avoidance"}},
                        {"node": {"refCode": "ISO 24113 §6.2", "title": "Disposal"}},
                    ]}}},
            ]}}
        if "evidences(where" in query:
            return {"evidences": {"edges": [
                {"node": {"id": "01E", "displayID": "EV-1", "name": "conj", "status": "READY",
                          "controls": {"edges": [{"node": {"refCode": "ISO 24113 §6.4"}}]}}},
            ]}}
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
    app.include_router(compliance.router)
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


AUTH = {"Authorization": "Bearer good"}


@pytest.mark.asyncio
async def test_status_requires_can_view() -> None:
    async with _client({"can_view": False}) as c:
        r = await c.get("/compliance/status", params={"org_id": "01O"}, headers=AUTH)
        assert r.status_code == 403
        assert "can_view" in r.json()["detail"]


@pytest.mark.asyncio
async def test_status_joins_evidence_to_controls() -> None:
    async with _client({"can_view": True}) as c:
        r = await c.get("/compliance/status", params={"org_id": "01O"}, headers=AUTH)
        assert r.status_code == 200
        body = r.json()
        assert body["org_id"] == "01O"
        iso = body["frameworks"][0]
        statuses = {ctrl["refCode"]: ctrl["status"] for ctrl in iso["controls"]}
        assert statuses["ISO 24113 §6.4"] == COMPLIANT      # has linked READY evidence
        assert statuses["ISO 24113 §6.2"] == NOT_ASSESSED   # nothing linked
        assert body["summary"] == {
            COMPLIANT: 1, PARTIAL: 0, NOT_ASSESSED: 1, "total": 2, "percentCompliant": 50.0,
        }

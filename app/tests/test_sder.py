"""M7 SDER-router tests: tetrad gating, Orekit + ITU + risk wiring, and Evidence
write-back. Orekit, theopenlane, and OpenFGA are stubbed; the L3 packages
(itu_compliance, risk_scoring) run for real.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.api import sder

TLE = {"line1": "1 25544U ...", "line2": "2 25544 ..."}
WINDOW = {"start": "2008-09-20T12:00:00Z", "end": "2008-09-20T13:00:00Z", "stepSeconds": 60}
BODY: dict[str, Any] = {"org_id": "01O", "tle1": TLE, "tle2": TLE, "window": WINDOW}
AUTH = {"Authorization": "Bearer good"}


class StubOrekit:
    def __init__(self, *, min_miss: float = 4.2, events: list[dict[str, Any]] | None = None) -> None:
        self._min = min_miss
        self._events = events or []

    async def conjunction(
        self, tle1: dict, tle2: dict, window: dict, *, threshold_km: float | None = None
    ) -> dict[str, Any]:
        return {"events": self._events, "minMissDistanceKm": self._min}


class StubOpenlane:
    def __init__(self, *, control_found: bool = True) -> None:
        self._control_found = control_found
        self.last_create: dict[str, Any] | None = None

    async def get_self(self, token: str) -> dict[str, Any]:
        return {"id": "01U", "email": "u@celestia.eu"} if token == "good" else {}

    async def execute(self, query: str, variables: dict | None = None, *, token: str | None = None) -> dict[str, Any]:
        if "controls(where" in query:
            edges = [{"node": {"id": "01C"}}] if self._control_found else []
            return {"controls": {"edges": edges}}
        if "createEvidence" in query:
            self.last_create = (variables or {})["i"]
            ev = {"id": "01E", "displayID": "EV-9", "name": self.last_create["name"]}
            return {"createEvidence": {"evidence": ev}}
        return {}


class StubOpenFGA:
    def __init__(self, allow: dict[str, bool]) -> None:
        self._allow = allow

    async def check(self, user: str, relation: str, obj: str, *, context: dict | None = None) -> bool:
        return self._allow.get(relation, False)


def _client(
    allow: dict[str, bool], *, orekit: StubOrekit | None = None, openlane: StubOpenlane | None = None
) -> tuple[httpx.AsyncClient, StubOpenlane]:
    app = FastAPI()
    ol = openlane or StubOpenlane()
    app.state.openlane = ol
    app.state.openfga = StubOpenFGA(allow)
    app.state.orekit = orekit or StubOrekit()
    app.include_router(sder.router)
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t"), ol


@pytest.mark.asyncio
async def test_operator_runs_conjunction_check_and_writes_evidence() -> None:
    client, ol = _client({"can_create_evidence": True})
    async with client as c:
        r = await c.post("/sder/conjunction-check", json=BODY, headers=AUTH)
        assert r.status_code == 201
        out = r.json()
        assert out["evidence_id"] == "01E"
        assert out["min_miss_distance_km"] == 4.2
        assert "risk_score" in out and "band" in out
        assert out["control_linked"] is True
    # Evidence written as a conjunction_report linked to the resolved control.
    assert ol.last_create is not None
    assert ol.last_create["name"].startswith("conjunction_report")
    assert ol.last_create["controlIDs"] == ["01C"]
    assert "conjunction_report" in ol.last_create["source"]


@pytest.mark.asyncio
async def test_insurer_blocked_at_bff() -> None:
    client, _ = _client({"can_create_evidence": False, "can_view": True})
    async with client as c:
        r = await c.post("/sder/conjunction-check", json=BODY, headers=AUTH)
        assert r.status_code == 403
        assert "can_create_evidence" in r.json()["detail"]


@pytest.mark.asyncio
async def test_itu_proximity_marks_compliant_when_protected_filing_colocated() -> None:
    body = {
        **BODY,
        "satellite_longitude_deg": 10.0,
        "filings": [
            {"network_name": "ALPHA", "longitude_deg": 10.0, "itu_administration": "F",
             "planned": False, "maturity": "brought_into_use"}
        ],
    }
    client, _ = _client({"can_create_evidence": True})
    async with client as c:
        r = await c.post("/sder/conjunction-check", json=body, headers=AUTH)
        assert r.status_code == 201
        assert r.json()["itu_compliant"] is True


@pytest.mark.asyncio
async def test_itu_proximity_not_compliant_when_only_early_stage() -> None:
    body = {
        **BODY,
        "satellite_longitude_deg": 50.0,
        "filings": [
            {"network_name": "ZETA", "longitude_deg": 50.0, "itu_administration": "G",
             "planned": False, "maturity": "early_stage"}
        ],
    }
    client, _ = _client({"can_create_evidence": True})
    async with client as c:
        r = await c.post("/sder/conjunction-check", json=body, headers=AUTH)
        assert r.json()["itu_compliant"] is False


@pytest.mark.asyncio
async def test_evidence_still_written_when_control_unresolved() -> None:
    client, ol = _client({"can_create_evidence": True}, openlane=StubOpenlane(control_found=False))
    async with client as c:
        r = await c.post("/sder/conjunction-check", json=BODY, headers=AUTH)
        assert r.status_code == 201
        assert r.json()["control_linked"] is False
    assert ol.last_create is not None
    assert "controlIDs" not in ol.last_create  # no link, but evidence still created


@pytest.mark.asyncio
async def test_risk_score_calculator_endpoint() -> None:
    client, _ = _client({})
    async with client as c:
        r = await c.get("/sder/risk-score", params={"min_miss_distance_km": 0.0}, headers=AUTH)
        assert r.status_code == 200
        body = r.json()
        assert body["band"] == "medium"  # conj 100 * 0.5 = 50, others neutral
        assert body["breakdown"]["conjunction"] == 50.0

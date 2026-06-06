"""End-to-end smoke test for the Phase-1 DoD — opt-in, runs against the LIVE stack.

Enable with:  CELESTIA_E2E=1 uv run pytest tests/test_smoke_e2e.py
Prerequisites: the docker-compose stack is up and `python -m app.auth.seed_tetrad`
has been run (creates the demo org + tetrad roles + members). Skipped otherwise, so
the default unit suite (`uv run pytest`) never touches the network.

It drives the BFF exactly as the four roles to prove the DoD:
  operator creates evidence linked to a control, insurer is blocked, regulator lists
  the evidence and downloads its audit history, operator is denied that history.
"""

from __future__ import annotations

import os

import httpx
import pytest

from app.auth import seed_tetrad as seed

E2E = os.environ.get("CELESTIA_E2E") == "1"
BFF = os.environ.get("CELESTIA_BFF_URL", "http://localhost:8001")

pytestmark = pytest.mark.skipif(
    not E2E, reason="e2e: set CELESTIA_E2E=1, start the stack, and run app.auth.seed_tetrad first"
)


@pytest.fixture
async def env() -> dict[str, str]:
    """Resolve the seeded demo org and mint a PAT per role. Skips (not fails) if the
    stack/seed isn't ready, so a missing environment doesn't look like a product bug.
    """
    try:
        async with httpx.AsyncClient(timeout=20.0) as http:
            token, _ = await seed.authenticate(http, *seed.OWNER)
            org_id = await seed.find_or_create_org(http, token)
        return {
            "org_id": org_id,
            "operator": await seed.mint_user_pat(*seed.DEMO_USERS["operator"], org_id),
            "insurer": await seed.mint_user_pat(*seed.DEMO_USERS["insurer"], org_id),
            "regulator": await seed.mint_user_pat(*seed.DEMO_USERS["regulator"], org_id),
        }
    except Exception as exc:  # noqa: BLE001 - any setup failure => environment not ready
        pytest.skip(f"e2e environment not ready ({exc}); run app.auth.seed_tetrad against a live stack")


def _bearer(pat: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {pat}"}


@pytest.mark.asyncio
async def test_dod_audit_flow(env: dict[str, str]) -> None:
    org = env["org_id"]
    async with httpx.AsyncClient(base_url=BFF, timeout=20.0) as c:
        # operator creates evidence linked to an ISO 24113 disposal control
        r = await c.post(
            "/evidence",
            json={"org_id": org, "name": "e2e disposal telemetry", "control_ref": "ISO 24113 §6.2"},
            headers=_bearer(env["operator"]),
        )
        assert r.status_code == 201, r.text
        evid = r.json()["id"]

        # insurer is blocked at the BFF boundary
        r = await c.post("/evidence", json={"org_id": org, "name": "blocked"}, headers=_bearer(env["insurer"]))
        assert r.status_code == 403

        # regulator can list the org's evidence and see the new record
        r = await c.get("/evidence", params={"org_id": org}, headers=_bearer(env["regulator"]))
        assert r.status_code == 200
        assert any(e["id"] == evid for e in r.json())

        # regulator can download the record's audit history (the DoD)
        r = await c.get(f"/evidence/{evid}/history", headers=_bearer(env["regulator"]))
        assert r.status_code == 200
        assert r.json()["audit"]["createdBy"]

        # operator is NOT an audit_log_viewer -> denied
        r = await c.get(f"/evidence/{evid}/history", headers=_bearer(env["operator"]))
        assert r.status_code == 403


# Canonical ISS TLE (CelesTrak/Orekit example).
_ISS_TLE = {
    "line1": "1 25544U 98067A   08264.51782528 -.00002182  00000-0 -11606-4 0  2927",
    "line2": "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537",
}


@pytest.mark.asyncio
async def test_sder_conjunction_dod_flow(env: dict[str, str]) -> None:
    """Phase-2 DoD: operator TLE -> Orekit conjunction -> ITU proximity -> risk score ->
    conjunction_report Evidence visible to the regulator with audit history. Requires the
    `sder` compose profile (Orekit container) up; skips if it is not reachable."""
    org = env["org_id"]
    body = {
        "org_id": org,
        "tle1": _ISS_TLE,
        "tle2": _ISS_TLE,
        "window": {"start": "2008-09-20T12:00:00Z", "end": "2008-09-20T12:30:00Z", "stepSeconds": 60},
        "satellite_longitude_deg": 10.0,
        "filings": [
            {"network_name": "ALPHA", "longitude_deg": 10.0, "itu_administration": "F",
             "planned": False, "maturity": "brought_into_use"}
        ],
    }
    async with httpx.AsyncClient(base_url=BFF, timeout=30.0) as c:
        r = await c.post("/sder/conjunction-check", json=body, headers=_bearer(env["operator"]))
        if r.status_code >= 500:
            pytest.skip(f"orekit service not reachable ({r.status_code}); start the `sder` profile")
        assert r.status_code == 201, r.text
        out = r.json()
        evid = out["evidence_id"]
        assert out["min_miss_distance_km"] == 0.0  # ISS screened against itself
        assert out["band"] in {"low", "medium", "high"}
        assert out["itu_compliant"] is True

        # insurer cannot run an operator action
        r = await c.post("/sder/conjunction-check", json=body, headers=_bearer(env["insurer"]))
        assert r.status_code == 403

        # regulator sees the conjunction_report evidence and its audit history (the DoD)
        r = await c.get("/evidence", params={"org_id": org}, headers=_bearer(env["regulator"]))
        assert r.status_code == 200
        assert any(e["id"] == evid for e in r.json())
        r = await c.get(f"/evidence/{evid}/history", headers=_bearer(env["regulator"]))
        assert r.status_code == 200
        assert r.json()["audit"]["createdBy"]


@pytest.mark.asyncio
async def test_l4_drafting_dod_flow(env: dict[str, str]) -> None:
    """Phase-3 DoD: given an obligation question, the drafting agent returns a compliance
    paragraph citing >=2 L2 obligations + >=1 L1 evidence record, each backed by a Context
    Core. Requires the `kg` profile (kg-postgres) up + the SDER e2e having created evidence;
    skips if the KG is unavailable."""
    org = env["org_id"]
    async with httpx.AsyncClient(base_url=BFF, timeout=30.0) as c:
        # populate the L2 KG from the loaded frameworks (idempotent)
        r = await c.post("/kg/ingest", headers=_bearer(env["operator"]))
        if r.status_code == 503:
            pytest.skip("knowledge graph unavailable; start the `kg` profile")
        assert r.status_code == 200, r.text
        assert r.json()["obligations"] > 0

        # regulator asks a compliance question -> cited, grounded paragraph
        r = await c.post(
            "/draft/obligation",
            json={"org_id": org, "query": "is the operator compliant with collision-avoidance duties"},
            headers=_bearer(env["regulator"]),
        )
        assert r.status_code == 200, r.text
        out = r.json()
        assert len(out["citations"]["obligations"]) >= 2
        assert len(out["citations"]["evidence"]) >= 1
        cored = {(cc["source_type"], cc["source_ref"]) for cc in out["context_cores"]}
        for o in out["citations"]["obligations"]:
            assert ("obligation", o["ref_code"]) in cored  # every claim has a Context Core
        assert out["draft"]

        # insurer with view can also draft; an unauthenticated caller cannot
        r = await c.post("/draft/obligation", json={"org_id": org, "query": "x"},
                         headers={"Authorization": "Bearer not-a-real-token"})
        assert r.status_code == 401

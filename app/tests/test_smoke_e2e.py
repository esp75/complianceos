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

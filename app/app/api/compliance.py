"""Compliance status — the operator dashboard's per-Framework/per-Control rollup (ADR-0015).

- GET /compliance/status?org_id=   per-Framework, per-Control compliance for an org, with an
                                   org-level summary. Requires ``can_view`` (operator / insurer /
                                   regulator / admin). The BFF owns the Standards×Evidence join so
                                   it stays server-side and tenancy-scoped; the openmct Compliance
                                   Status panel renders this payload directly.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import assert_can, current_user, get_openfga, get_openlane
from app.clients.openfga import OpenFGAClient
from app.clients.openlane import OpenlaneClient
from app.l5.rollup import rollup_status

router = APIRouter(prefix="/compliance", tags=["compliance"])

# Standards + their controls (refCode/title). Same shape frameworks.py reads; duplicated here
# to keep each router's GraphQL local (the OpenlaneClient is the single transport boundary,
# ADR-0012, not a query registry).
_STANDARDS = """
{ standards { edges { node {
  id shortName framework
  controls { edges { node { refCode title } } }
} } } }
"""

# Org evidence with the controls each record is linked to (the join key is the control refCode).
_EVIDENCE = """
query($o:ID!){ evidences(where:{ownerID:$o}){ edges { node {
  id displayID name status
  controls { edges { node { refCode } } }
} } } }
"""


def _evidence_with_refs(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Project theopenlane evidence edges into the flat shape rollup_status expects."""
    out: list[dict[str, Any]] = []
    for edge in data.get("evidences", {}).get("edges", []):
        node = edge["node"]
        refs = [
            c["node"]["refCode"]
            for c in node.get("controls", {}).get("edges", [])
            if c.get("node", {}).get("refCode")
        ]
        out.append({
            "id": node.get("id"),
            "displayID": node.get("displayID"),
            "name": node.get("name"),
            "status": node.get("status"),
            "controlRefs": refs,
        })
    return out


def _frameworks(data: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for edge in data.get("standards", {}).get("edges", []):
        n = edge["node"]
        out.append({
            "shortName": n.get("shortName"),
            "framework": n.get("framework"),
            "controls": [c["node"] for c in n.get("controls", {}).get("edges", [])],
        })
    return out


async def gather_status(openlane: OpenlaneClient, token: str, org_id: str) -> dict[str, Any]:
    """Fetch + roll up an org's per-Framework/per-Control compliance status.

    The single owner of the Standards×Evidence join (ADR-0012 keeps GraphQL local to this router).
    Reused by the Compliance Status panel endpoint and the trust/bundle signer.
    """
    standards = await openlane.execute(_STANDARDS, token=token)
    evidence = await openlane.execute(_EVIDENCE, {"o": org_id}, token=token)
    return rollup_status(_frameworks(standards), _evidence_with_refs(evidence))


@router.get("/status")
async def compliance_status(
    org_id: Annotated[str, Query(description="organization ULID")],
    user: Annotated[dict[str, Any], Depends(current_user)],
    openlane: Annotated[OpenlaneClient, Depends(get_openlane)],
    openfga: Annotated[OpenFGAClient, Depends(get_openfga)],
) -> dict[str, Any]:
    await assert_can(openfga, user, "can_view", f"organization:{org_id}")
    result = await gather_status(openlane, user["_token"], org_id)
    return {"org_id": org_id, **result}

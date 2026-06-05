"""Evidence endpoints — where the tetrad gates real operations (ADR-0012).

- POST /evidence            create evidence in an org, optionally linked to a control.
                            Requires ``can_create_evidence`` (operator/admin) — insurer
                            and regulator are blocked at the BFF before theopenlane is hit.
- GET  /evidence?org_id=    list an org's evidence. Requires ``can_view``.
- GET  /evidence/{id}/history  audit trail (createdAt/by, updatedAt/by). Requires
                            ``audit_log_viewer`` (regulator/admin) — this is the DoD path.
"""

from __future__ import annotations

from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api.deps import assert_can, current_user, get_openfga, get_openlane
from app.clients.openfga import OpenFGAClient
from app.clients.openlane import OpenlaneClient

router = APIRouter(prefix="/evidence", tags=["evidence"])


class EvidenceCreate(BaseModel):
    org_id: str
    name: str
    description: str | None = None
    control_ref: str | None = None  # e.g. "EU-SA Art.3" — linked if it resolves
    source: str | None = None


async def _resolve_control(openlane: OpenlaneClient, token: str, ref_code: str) -> str | None:
    data = await openlane.execute(
        "query($r:String!){ controls(where:{refCode:$r}){ edges{ node{ id } } } }",
        {"r": ref_code}, token=token,
    )
    edges = data.get("controls", {}).get("edges", [])
    return str(edges[0]["node"]["id"]) if edges else None


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_evidence(
    body: EvidenceCreate,
    user: Annotated[dict[str, Any], Depends(current_user)],
    openlane: Annotated[OpenlaneClient, Depends(get_openlane)],
    openfga: Annotated[OpenFGAClient, Depends(get_openfga)],
) -> dict[str, Any]:
    await assert_can(openfga, user, "can_create_evidence", f"organization:{body.org_id}")

    inp: dict[str, Any] = {"name": body.name, "ownerID": body.org_id}
    if body.description:
        inp["description"] = body.description
    if body.source:
        inp["source"] = body.source
    if body.control_ref:
        cid = await _resolve_control(openlane, user["_token"], body.control_ref)
        if cid is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"control {body.control_ref} not found")
        inp["controlIDs"] = [cid]

    data = await openlane.execute(
        "mutation($i:CreateEvidenceInput!){ createEvidence(input:$i){ evidence{ id displayID name } } }",
        {"i": inp}, token=user["_token"],
    )
    return cast("dict[str, Any]", data["createEvidence"]["evidence"])


@router.get("")
async def list_evidence(
    org_id: Annotated[str, Query(description="organization ULID")],
    user: Annotated[dict[str, Any], Depends(current_user)],
    openlane: Annotated[OpenlaneClient, Depends(get_openlane)],
    openfga: Annotated[OpenFGAClient, Depends(get_openfga)],
) -> list[dict[str, Any]]:
    await assert_can(openfga, user, "can_view", f"organization:{org_id}")
    data = await openlane.execute(
        "query($o:ID!){ evidences(where:{ownerID:$o}){ edges{ node{ id displayID name status } } } }",
        {"o": org_id}, token=user["_token"],
    )
    return [e["node"] for e in data.get("evidences", {}).get("edges", [])]


@router.get("/{evidence_id}/history")
async def evidence_history(
    evidence_id: str,
    user: Annotated[dict[str, Any], Depends(current_user)],
    openlane: Annotated[OpenlaneClient, Depends(get_openlane)],
    openfga: Annotated[OpenFGAClient, Depends(get_openfga)],
) -> dict[str, Any]:
    data = await openlane.execute(
        "query($id:ID!){ evidence(id:$id){ id displayID name status createdAt updatedAt "
        "createdBy updatedBy owner{ id } } }",
        {"id": evidence_id}, token=user["_token"],
    )
    ev = data.get("evidence")
    if not ev:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="evidence not found")
    org_id = (ev.get("owner") or {}).get("id")
    await assert_can(openfga, user, "audit_log_viewer", f"organization:{org_id}")
    return {
        "id": ev["id"],
        "displayID": ev.get("displayID"),
        "name": ev.get("name"),
        "status": ev.get("status"),
        "audit": {
            "createdAt": ev.get("createdAt"),
            "createdBy": ev.get("createdBy"),
            "updatedAt": ev.get("updatedAt"),
            "updatedBy": ev.get("updatedBy"),
        },
    }

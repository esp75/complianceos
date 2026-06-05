"""Frameworks (theopenlane Standards + Controls), read-only.

Forwarding the caller's token lets theopenlane scope the result to what the user may
view; no extra BFF check is needed for a read of the user's own visible standards.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.deps import current_user, get_openlane
from app.clients.openlane import OpenlaneClient

router = APIRouter(prefix="/frameworks", tags=["frameworks"])

_LIST = """
{ standards { edges { node {
  id shortName framework description
  controls { totalCount edges { node { refCode title } } }
} } } }
"""


@router.get("")
async def list_frameworks(
    user: Annotated[dict[str, Any], Depends(current_user)],
    openlane: Annotated[OpenlaneClient, Depends(get_openlane)],
) -> list[dict[str, Any]]:
    data = await openlane.execute(_LIST, token=user["_token"])
    out: list[dict[str, Any]] = []
    for edge in data.get("standards", {}).get("edges", []):
        n = edge["node"]
        out.append({
            "id": n["id"],
            "shortName": n.get("shortName"),
            "framework": n.get("framework"),
            "controlCount": n.get("controls", {}).get("totalCount", 0),
            "controls": [c["node"] for c in n.get("controls", {}).get("edges", [])],
        })
    return out

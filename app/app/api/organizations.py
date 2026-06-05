"""Organizations the caller belongs to, read-only (theopenlane scopes via the token)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.deps import current_user, get_openlane
from app.clients.openlane import OpenlaneClient

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("")
async def list_organizations(
    user: Annotated[dict[str, Any], Depends(current_user)],
    openlane: Annotated[OpenlaneClient, Depends(get_openlane)],
) -> list[dict[str, Any]]:
    data = await openlane.execute(
        "{ organizations { edges { node { id name displayName } } } }",
        token=user["_token"],
    )
    return [e["node"] for e in data.get("organizations", {}).get("edges", [])]

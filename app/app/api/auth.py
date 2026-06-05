"""Auth demonstration endpoints for M2.

- ``GET /auth/me``   — resolves the bearer token to a theopenlane user (auth seam).
- ``GET /auth/can``  — runs an OpenFGA check for the current user at the BFF boundary
                       (ADR-0012). Demonstrates the tetrad: e.g.
                       /auth/can?relation=can_create_evidence&object=organization:<id>

Full per-route enforcement on domain endpoints arrives in M4; these endpoints prove
the authn + authz wiring end to end.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import current_user, get_openfga
from app.clients.openfga import OpenFGAClient

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
async def me(user: Annotated[dict[str, Any], Depends(current_user)]) -> dict[str, Any]:
    return {k: v for k, v in user.items() if not k.startswith("_")}


@router.get("/can")
async def can(
    user: Annotated[dict[str, Any], Depends(current_user)],
    openfga: Annotated[OpenFGAClient, Depends(get_openfga)],
    relation: Annotated[str, Query(description="FGA relation, e.g. can_create_evidence")],
    object: Annotated[str, Query(description="FGA object, e.g. organization:<ULID>")],
) -> dict[str, object]:
    allowed = await openfga.check(f"user:{user['id']}", relation, object)
    return {"user": f"user:{user['id']}", "relation": relation, "object": object, "allowed": allowed}

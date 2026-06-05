"""Shared FastAPI dependencies for the BFF.

The current-user dependency resolves a bearer token to a theopenlane user via the
``self`` query. This is the BFF's authentication seam; M4 domain routers layer the
OpenFGA authorization check (ADR-0012) on top of it.
"""

from __future__ import annotations

from typing import Annotated, Any, cast

from fastapi import Depends, Header, HTTPException, Request, status

from app.clients.openfga import OpenFGAClient
from app.clients.openlane import OpenlaneClient, OpenlaneError


def get_openlane(request: Request) -> OpenlaneClient:
    return cast(OpenlaneClient, request.app.state.openlane)


def get_openfga(request: Request) -> OpenFGAClient:
    return cast(OpenFGAClient, request.app.state.openfga)


def bearer_token(authorization: Annotated[str | None, Header()] = None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return authorization.split(" ", 1)[1].strip()


async def current_user(
    token: Annotated[str, Depends(bearer_token)],
    openlane: Annotated[OpenlaneClient, Depends(get_openlane)],
) -> dict[str, Any]:
    """Resolve the authenticated user, or 401. Stashes the token under ``_token``
    so downstream calls can forward the user's credential to theopenlane.
    """
    try:
        user = await openlane.get_self(token)
    except OpenlaneError:
        user = {}
    if not user.get("id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or unauthorized token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {**user, "_token": token}

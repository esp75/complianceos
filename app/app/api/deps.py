"""Shared FastAPI dependencies for the BFF.

The current-user dependency resolves a bearer token to a theopenlane user via the
``self`` query. This is the BFF's authentication seam; M4 domain routers layer the
OpenFGA authorization check (ADR-0012) on top of it.
"""

from __future__ import annotations

from typing import Annotated, Any, cast

from fastapi import Depends, Header, HTTPException, Request, status

from app.clients.openfga import OpenFGAClient, OpenFGAError
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


async def assert_can(
    openfga: OpenFGAClient, user: dict[str, Any], relation: str, obj: str
) -> None:
    """BFF-boundary authorization (ADR-0012). Raise 403 unless the user has ``relation``
    on ``obj``. Fail-closed: an OpenFGA error denies. Supplies the user's email domain as
    condition context (the org ``access`` relation is gated by ``email_domains_allowed``).
    """
    email = user.get("email", "")
    domain = email.split("@", 1)[1] if "@" in email else ""
    try:
        allowed = await openfga.check(
            f"user:{user['id']}", relation, obj,
            context={"email_domain": domain} if domain else None,
        )
    except OpenFGAError:
        allowed = False
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"forbidden: requires '{relation}' on {obj}",
        )

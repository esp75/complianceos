"""Shared FastAPI dependencies for the BFF.

The current-user dependency resolves a bearer token to a theopenlane user via the
``self`` query. This is the BFF's authentication seam; M4 domain routers layer the
OpenFGA authorization check (ADR-0012) on top of it.
"""

from __future__ import annotations

from typing import Annotated, Any, cast

from fastapi import Depends, Header, HTTPException, Request, status

from app.api.bundle.sign_pdf import BundleSigner
from app.api.trust.keystore import KeyStore
from app.api.trust.store import TrustStore
from app.clients.kg import KGClient
from app.clients.openfga import OpenFGAClient, OpenFGAError
from app.clients.openlane import OpenlaneClient, OpenlaneError
from app.clients.orekit import OrekitClient
from app.kg.embeddings import EmbeddingProvider
from app.llm.base import LLMProvider


def get_openlane(request: Request) -> OpenlaneClient:
    return cast(OpenlaneClient, request.app.state.openlane)


def get_openfga(request: Request) -> OpenFGAClient:
    return cast(OpenFGAClient, request.app.state.openfga)


def get_orekit(request: Request) -> OrekitClient:
    return cast(OrekitClient, request.app.state.orekit)


def get_kg(request: Request) -> KGClient:
    return cast(KGClient, request.app.state.kg)


def get_embed(request: Request) -> EmbeddingProvider:
    return cast(EmbeddingProvider, request.app.state.embed)


def get_llm(request: Request) -> LLMProvider | None:
    return cast("LLMProvider | None", request.app.state.llm)


async def require_kg(kg: Annotated[KGClient, Depends(get_kg)]) -> KGClient:
    """503 unless the L2 KG (kg-postgres, `kg` profile) is reachable."""
    if not await kg.ping():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="knowledge graph unavailable (start the `kg` compose profile)",
        )
    return kg


def get_trust(request: Request) -> TrustStore:
    return cast(TrustStore, request.app.state.trust)


def get_keystore(request: Request) -> KeyStore:
    return cast(KeyStore, request.app.state.trust_keystore)


def get_bundle_signer(request: Request) -> BundleSigner:
    return cast(BundleSigner, request.app.state.bundle_signer)


async def require_trust(trust: Annotated[TrustStore, Depends(get_trust)]) -> TrustStore:
    """503 unless the trust store (bundle/audit chain Postgres) is reachable."""
    if not await trust.ping():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="trust store unavailable (start the `kg` compose profile and set "
                   "CELESTIA_TRUST_SIGNING_SEED)",
        )
    return trust


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

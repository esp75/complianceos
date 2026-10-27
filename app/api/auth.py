"""OIDC bearer-token verification against a Zitadel issuer.

Config (env):
  ZITADEL_ISSUER    e.g. https://auth.example.com (must match the token's iss claim)
  ZITADEL_AUDIENCE  the project/client id the token was issued for (aud claim)

There is deliberately no "auth disabled" switch. Every protected route needs a valid token.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import jwt
from fastapi import HTTPException, Request

ALGORITHMS = ["RS256"]


@dataclass(frozen=True)
class Principal:
    subject: str
    tenant: str | None


def decode_token(token: str, key: Any, *, issuer: str, audience: str) -> Principal:
    """Verify signature, expiry, issuer and audience. Raises HTTP 401 on any failure."""
    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=ALGORITHMS,
            audience=audience,
            issuer=issuer,
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="invalid token") from exc
    tenant = claims.get("urn:zitadel:iam:org:id")
    return Principal(subject=str(claims["sub"]), tenant=str(tenant) if tenant else None)


def current_principal(request: Request) -> Principal:
    auth_header = request.headers.get("authorization", "")
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="missing bearer token")

    issuer: str | None = request.app.state.zitadel_issuer
    audience: str | None = request.app.state.zitadel_audience
    jwks: jwt.PyJWKClient | None = request.app.state.jwks_client
    if not issuer or not audience or jwks is None:
        raise HTTPException(status_code=503, detail="auth not configured")

    # Reject malformed or unexpected headers before any network lookup, so an
    # attacker cannot make the API fetch JWKS by sending junk tokens.
    try:
        jwt_header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="malformed token") from exc
    if jwt_header.get("alg") != "RS256" or not isinstance(jwt_header.get("kid"), str):
        raise HTTPException(status_code=401, detail="unsupported token header")

    try:
        signing_key = jwks.get_signing_key(jwt_header["kid"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="unknown signing key") from exc
    return decode_token(token, signing_key.key, issuer=issuer, audience=audience)

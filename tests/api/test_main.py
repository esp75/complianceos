from __future__ import annotations

import base64
import json
import os
import time
from collections.abc import Iterator

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from app.api.auth import Principal, current_principal, decode_token
from app.api.main import app

ISSUER = "https://auth.test"
AUDIENCE = "complianceos-web"


@pytest.fixture(scope="module")
def rsa_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _token(key: rsa.RSAPrivateKey, **overrides: object) -> str:
    now = int(time.time())
    claims: dict[str, object] = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": "user-1",
        "exp": now + 300,
        "iat": now,
        "urn:zitadel:iam:org:id": "org-1",
    }
    claims.update(overrides)
    return jwt.encode(claims, key, algorithm="RS256")


def test_valid_token_yields_principal(rsa_key: rsa.RSAPrivateKey) -> None:
    p = decode_token(_token(rsa_key), rsa_key.public_key(), issuer=ISSUER, audience=AUDIENCE)
    assert p == Principal(subject="user-1", tenant="org-1")


@pytest.mark.parametrize(
    "overrides",
    [
        {"aud": "someone-else"},
        {"iss": "https://evil.test"},
        {"exp": int(time.time()) - 10},
        {"sub": None},
    ],
)
def test_bad_claims_are_401(rsa_key: rsa.RSAPrivateKey, overrides: dict[str, object]) -> None:
    token = _token(rsa_key, **overrides)
    with pytest.raises(HTTPException) as exc:
        decode_token(token, rsa_key.public_key(), issuer=ISSUER, audience=AUDIENCE)
    assert exc.value.status_code == 401


def test_wrong_key_is_401(rsa_key: rsa.RSAPrivateKey) -> None:
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(HTTPException) as exc:
        decode_token(_token(rsa_key), other.public_key(), issuer=ISSUER, audience=AUDIENCE)
    assert exc.value.status_code == 401


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def test_alg_none_is_rejected(rsa_key: rsa.RSAPrivateKey) -> None:
    # Hand-built unsigned token: header alg=none, empty signature segment.
    header = _b64(json.dumps({"alg": "none", "typ": "JWT"}).encode())
    payload = _b64(
        json.dumps(
            {"iss": ISSUER, "aud": AUDIENCE, "sub": "x", "exp": int(time.time()) + 60}
        ).encode()
    )
    unsigned = f"{header}.{payload}."
    with pytest.raises(HTTPException) as exc:
        decode_token(unsigned, rsa_key.public_key(), issuer=ISSUER, audience=AUDIENCE)
    assert exc.value.status_code == 401


@pytest.fixture
def client() -> Iterator[httpx.AsyncClient]:
    # Lifespan is not run under ASGITransport, so no DB or JWKS is contacted.
    app.state.pool = None
    app.state.zitadel_issuer = None
    app.state.zitadel_audience = None
    app.state.jwks_client = None
    yield httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
    app.dependency_overrides.clear()


async def test_health_is_ok(client: httpx.AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_obligations_requires_bearer_token(client: httpx.AsyncClient) -> None:
    resp = await client.get("/obligations")
    assert resp.status_code == 401


async def test_obligations_503_when_auth_unconfigured(client: httpx.AsyncClient) -> None:
    resp = await client.get("/obligations", headers={"authorization": "Bearer abc"})
    assert resp.status_code == 503


async def test_obligations_rejects_bad_limit_before_querying(
    client: httpx.AsyncClient,
) -> None:
    # Bypass auth so the request reaches validation. The sentinel pool is never used
    # because validation fails before pool.acquire().
    app.dependency_overrides[current_principal] = lambda: Principal(subject="u", tenant="t")
    app.state.pool = object()
    assert (await client.get("/obligations", params={"limit": 0})).status_code == 422
    assert (await client.get("/obligations", params={"offset": -1})).status_code == 422


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="needs DATABASE_URL")
async def test_obligations_empty_list_against_real_db() -> None:
    app.dependency_overrides[current_principal] = lambda: Principal(subject="u", tenant="t")
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as c:
            resp = await c.get("/obligations")
    app.dependency_overrides.clear()
    assert resp.status_code == 200
    assert resp.json()["items"] == []


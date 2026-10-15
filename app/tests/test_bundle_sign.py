"""/bundle/sign endpoint tests (ADR-0016): auth gate, PDF output, offline-verifiable signature,
Merkle root, tamper-evident chain append, trust-store availability. theopenlane/OpenFGA/trust store
are stubbed; the keystore + PDF signer are the real v0 implementations (offline, deterministic).
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.api.bundle import sign as bundle_sign
from app.api.bundle.manifest import build_leaves, build_manifest, canonical_bytes
from app.api.bundle.sign_pdf import DetachedEd25519PdfSigner
from app.api.compliance import gather_status
from app.api.trust.keys import key_fingerprint, public_raw
from app.api.trust.keystore import DerivedKeyStore
from app.api.trust.merkle import merkle_root
from app.api.trust.signing import verify

TEST_SEED = b"endpoint-test-master-seed-000001"
AUTH = {"Authorization": "Bearer good"}


class StubOpenlane:
    async def get_self(self, token: str) -> dict[str, Any]:
        return {"id": "01U", "email": "u@celestia.eu"} if token == "good" else {}

    async def execute(
        self, query: str, variables: dict | None = None, *, token: str | None = None
    ) -> dict[str, Any]:
        if "standards" in query:
            return {"standards": {"edges": [
                {"node": {"id": "01S", "shortName": "ISO-24113", "framework": "2023", "controls": {
                    "edges": [
                        {"node": {"refCode": "ISO 24113 §6.4", "title": "Collision avoidance"}},
                        {"node": {"refCode": "ISO 24113 §6.2", "title": "Disposal"}},
                    ]}}},
            ]}}
        if "createdAt" in query:  # _EVIDENCE_AUDIT
            return {"evidences": {"edges": [
                {"node": {"id": "01E", "displayID": "EV-1", "status": "READY",
                          "createdAt": "t0", "createdBy": "u", "updatedAt": "t1", "updatedBy": "u",
                          "controls": {"edges": [{"node": {"refCode": "ISO 24113 §6.4"}}]}}},
            ]}}
        if "evidences(where" in query:  # rollup evidence
            return {"evidences": {"edges": [
                {"node": {"id": "01E", "displayID": "EV-1", "name": "conj", "status": "READY",
                          "controls": {"edges": [{"node": {"refCode": "ISO 24113 §6.4"}}]}}},
            ]}}
        return {}


class StubOpenFGA:
    def __init__(self, allow: dict[str, bool]) -> None:
        self._allow = allow

    async def check(self, user: str, relation: str, obj: str, *, context: dict | None = None) -> bool:
        return self._allow.get(relation, False)


class StubTrustStore:
    def __init__(self, *, up: bool = True) -> None:
        self._up = up
        self._roots: dict[str, bytes] = {}
        self.appends: list[dict[str, Any]] = []
        self.keys: list[tuple[str, bytes, str]] = []

    async def ping(self) -> bool:
        return self._up

    async def last_root(self, org_id: str) -> bytes | None:
        return self._roots.get(org_id)

    async def upsert_org_key(self, org_id: str, public_key: bytes, fingerprint: str) -> None:
        self.keys.append((org_id, public_key, fingerprint))

    async def append_bundle(
        self, org_id: str, merkle_root: bytes, prev_root: bytes | None,
        chain_hash: bytes, signature: bytes, manifest: str,
    ) -> int:
        self.appends.append({
            "org_id": org_id, "merkle_root": merkle_root, "prev_root": prev_root,
            "chain_hash": chain_hash, "signature": signature, "manifest": manifest,
        })
        self._roots[org_id] = merkle_root
        return len(self.appends)


def _client(allow: dict[str, bool], *, trust: StubTrustStore | None = None) -> httpx.AsyncClient:
    app = FastAPI()
    app.state.openlane = StubOpenlane()
    app.state.openfga = StubOpenFGA(allow)
    app.state.trust = trust if trust is not None else StubTrustStore()
    app.state.trust_keystore = DerivedKeyStore(TEST_SEED)
    app.state.bundle_signer = DetachedEd25519PdfSigner()
    app.include_router(bundle_sign.router)
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


async def _reconstruct(org_id: str, issued_at: str) -> bytes:
    """Rebuild the exact canonical manifest bytes the endpoint signed, from the same stub data."""
    openlane = StubOpenlane()
    compliance = await gather_status(openlane, "good", org_id)
    audit_data = await openlane.execute(bundle_sign._EVIDENCE_AUDIT, {"o": org_id}, token="good")
    evidence_audit = bundle_sign._evidence_audit(audit_data)
    leaves = build_leaves(compliance, evidence_audit)
    root = merkle_root(leaves)
    fp = key_fingerprint(public_raw(DerivedKeyStore(TEST_SEED).signing_key(org_id)))
    manifest = build_manifest(
        org_id, compliance, evidence_audit,
        root_hex=root.hex(), leaves_hex=[leaf.hex() for leaf in leaves],
        fingerprint=fp, issued_at=issued_at,
    )
    return canonical_bytes(manifest)


@pytest.mark.asyncio
async def test_sign_requires_can_view() -> None:
    async with _client({"can_view": False}) as c:
        r = await c.post("/bundle/sign", params={"org_id": "01O"}, headers=AUTH)
        assert r.status_code == 403
        assert "can_view" in r.json()["detail"]


@pytest.mark.asyncio
async def test_sign_returns_pdf() -> None:
    async with _client({"can_view": True}) as c:
        r = await c.post("/bundle/sign", params={"org_id": "01O"}, headers=AUTH)
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        assert r.content.startswith(b"%PDF")
        assert "attachment" in r.headers["content-disposition"]


@pytest.mark.asyncio
async def test_sign_signature_verifies_offline() -> None:
    async with _client({"can_view": True}) as c:
        r = await c.post("/bundle/sign", params={"org_id": "01O"}, headers=AUTH)
        assert r.status_code == 200
        sig = bytes.fromhex(r.headers["x-trust-signature"])
        manifest_bytes = await _reconstruct("01O", r.headers["x-trust-issued-at"])
        pub = DerivedKeyStore(TEST_SEED).public_key("01O")
        assert verify(manifest_bytes, sig, pub)


@pytest.mark.asyncio
async def test_sign_merkle_root_matches_recomputation() -> None:
    async with _client({"can_view": True}) as c:
        r = await c.post("/bundle/sign", params={"org_id": "01O"}, headers=AUTH)
        openlane = StubOpenlane()
        compliance = await gather_status(openlane, "good", "01O")
        audit_data = await openlane.execute(bundle_sign._EVIDENCE_AUDIT, {"o": "01O"}, token="good")
        leaves = build_leaves(compliance, bundle_sign._evidence_audit(audit_data))
        assert r.headers["x-trust-merkle-root"] == merkle_root(leaves).hex()


@pytest.mark.asyncio
async def test_sign_appends_tamper_evident_chain() -> None:
    trust = StubTrustStore()
    async with _client({"can_view": True}, trust=trust) as c:
        await c.post("/bundle/sign", params={"org_id": "01O"}, headers=AUTH)
        await c.post("/bundle/sign", params={"org_id": "01O"}, headers=AUTH)
    assert len(trust.appends) == 2
    assert trust.appends[0]["prev_root"] is None
    assert trust.appends[1]["prev_root"] == trust.appends[0]["merkle_root"]


@pytest.mark.asyncio
async def test_sign_requires_trust_store() -> None:
    async with _client({"can_view": True}, trust=StubTrustStore(up=False)) as c:
        r = await c.post("/bundle/sign", params={"org_id": "01O"}, headers=AUTH)
        assert r.status_code == 503

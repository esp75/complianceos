# MARKED-FOR-EXTERNAL-REVIEW — Trail of Bits / Quarkslab / Cure53
"""Signed compliance evidence bundle endpoint (Phase 4, ADR-0016).

POST /bundle/sign?org_id=   Gather the org's compliance status + evidence audit metadata, seal it
                            under a SHA-256 Merkle root, sign the canonical manifest with the org's
                            derived Ed25519 key, render a self-verifying PDF, append the root to the
                            org's tamper-evident bundle chain, and return the PDF. Gated by
                            ``can_edit`` on the organization (org admins and owners): signing
                            makes the org's key speak for the org, which is stronger than reading
                            the same data. A ``framework`` filter is recorded in the signed
                            manifest's ``scope``.
"""

from __future__ import annotations

import datetime as _dt
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.bundle.manifest import build_leaves, build_manifest, canonical_bytes
from app.api.bundle.sign_pdf import BundleSigner
from app.api.compliance import gather_status
from app.api.deps import (
    assert_can,
    current_user,
    get_bundle_signer,
    get_keystore,
    get_openfga,
    get_openlane,
    require_trust,
)
from app.api.trust.keys import key_fingerprint, public_raw
from app.api.trust.keystore import KeyStore, KeyStoreUnavailable
from app.api.trust.merkle import merkle_root
from app.api.trust.signing import sign
from app.api.trust.store import TrustStore
from app.clients.openfga import OpenFGAClient
from app.clients.openlane import OpenlaneClient

router = APIRouter(prefix="/bundle", tags=["bundle"])

# Org evidence with the audit metadata + control linkage the bundle seals.
_EVIDENCE_AUDIT = """
query($o:ID!){ evidences(where:{ownerID:$o}){ edges { node {
  id displayID status createdAt createdBy updatedAt updatedBy
  controls { edges { node { refCode } } }
} } } }
"""


def _evidence_audit(data: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for edge in data.get("evidences", {}).get("edges", []):
        node = edge["node"]
        refs = [
            c["node"]["refCode"]
            for c in node.get("controls", {}).get("edges", [])
            if c.get("node", {}).get("refCode")
        ]
        out.append({
            "id": node.get("id"),
            "displayID": node.get("displayID"),
            "status": node.get("status"),
            "controlRefs": refs,
            "audit": {
                "createdAt": node.get("createdAt"),
                "createdBy": node.get("createdBy"),
                "updatedAt": node.get("updatedAt"),
                "updatedBy": node.get("updatedBy"),
            },
        })
    return out


@router.post("/sign")
async def sign_bundle(
    org_id: Annotated[str, Query(description="organization ULID")],
    user: Annotated[dict[str, Any], Depends(current_user)],
    openlane: Annotated[OpenlaneClient, Depends(get_openlane)],
    openfga: Annotated[OpenFGAClient, Depends(get_openfga)],
    trust: Annotated[TrustStore, Depends(require_trust)],
    keystore: Annotated[KeyStore, Depends(get_keystore)],
    signer: Annotated[BundleSigner, Depends(get_bundle_signer)],
    framework: Annotated[str | None, Query(description="optional shortName filter")] = None,
) -> Response:
    # Export signs with the org key: an org-level write, not a read (THREAT_MODEL finding 2).
    await assert_can(openfga, user, "can_edit", f"organization:{org_id}")
    token = user["_token"]

    compliance = await gather_status(openlane, token, org_id)
    if framework:
        compliance = {
            **compliance,
            "frameworks": [
                fw for fw in compliance.get("frameworks", []) if fw.get("shortName") == framework
            ],
        }
    audit_data = await openlane.execute(_EVIDENCE_AUDIT, {"o": org_id}, token=token)
    evidence_audit = _evidence_audit(audit_data)

    # Seal the contents under a Merkle root.
    leaves = build_leaves(compliance, evidence_audit)
    root = merkle_root(leaves)

    # Derive the org's signing key (503 if the master seed is unconfigured).
    try:
        priv = keystore.signing_key(org_id)
    except KeyStoreUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="trust signing key unavailable (set COMPLIANCEOS_TRUST_SIGNING_SEED)",
        ) from exc
    pub = public_raw(priv)
    fingerprint = key_fingerprint(pub)

    issued_at = _dt.datetime.now(_dt.UTC).replace(microsecond=0).isoformat()
    manifest = build_manifest(
        org_id, compliance, evidence_audit,
        root_hex=root.hex(),
        leaves_hex=[leaf.hex() for leaf in leaves],
        fingerprint=fingerprint,
        issued_at=issued_at,
        framework_filter=framework or None,
    )
    manifest_bytes = canonical_bytes(manifest)
    signature = sign(manifest_bytes, priv)

    pdf = signer.render_and_sign(manifest, manifest_bytes, signature, pub)

    # Append to the org's tamper-evident bundle chain: head read + insert under one per-org lock.
    await trust.upsert_org_key(org_id, pub, fingerprint)
    await trust.append_next(org_id, root, signature, manifest_bytes.decode("utf-8"))

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="bundle-{org_id}.pdf"',
            "X-Trust-Merkle-Root": root.hex(),
            "X-Trust-Signature": signature.hex(),
            "X-Trust-Key-Fingerprint": fingerprint,
            "X-Trust-Issued-At": issued_at,
        },
    )

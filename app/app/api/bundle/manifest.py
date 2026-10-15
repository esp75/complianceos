# MARKED-FOR-EXTERNAL-REVIEW — Trail of Bits / Quarkslab / Cure53
"""Canonical bundle manifest + Merkle leaf set (Phase 4, ADR-0016).

Pure functions. Canonicalisation (sorted keys, compact separators, UTF-8) is security-critical: the
signature is computed over ``canonical_bytes(manifest)``, so the same logical content must always
serialise to the same bytes for a signature to re-verify. The leaf set is emitted in a fixed order
(controls by refCode, then evidence by id) so the Merkle root is reproducible by any verifier.
"""

from __future__ import annotations

import json
from typing import Any

from app.api.trust.merkle import leaf_hash

MANIFEST_VERSION = "trust-bundle/v0"


def canonical_bytes(obj: dict[str, Any]) -> bytes:
    """Deterministic JSON encoding used as the signing input."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _control_records(status: dict[str, Any]) -> list[dict[str, Any]]:
    """Flat, sorted (refCode) control records from a rollup status payload."""
    records: list[dict[str, Any]] = []
    for fw in status.get("frameworks", []):
        for ctrl in fw.get("controls", []):
            records.append({
                "type": "control",
                "refCode": ctrl.get("refCode"),
                "status": ctrl.get("status"),
                "evidenceCount": ctrl.get("evidenceCount", 0),
            })
    records.sort(key=lambda r: str(r["refCode"]))
    return records


def _evidence_records(evidence_audit: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sorted (id) evidence records with audit metadata."""
    records: list[dict[str, Any]] = []
    for ev in evidence_audit:
        records.append({
            "type": "evidence",
            "id": ev.get("id"),
            "displayID": ev.get("displayID"),
            "status": ev.get("status"),
            "controlRefs": sorted(ev.get("controlRefs", [])),
            "audit": ev.get("audit", {}),
        })
    records.sort(key=lambda r: str(r["id"]))
    return records


def build_leaves(status: dict[str, Any], evidence_audit: list[dict[str, Any]]) -> list[bytes]:
    """Ordered Merkle leaf hashes: every control status, then every evidence record."""
    ordered = _control_records(status) + _evidence_records(evidence_audit)
    return [leaf_hash(canonical_bytes(rec)) for rec in ordered]


def build_manifest(
    org_id: str,
    status: dict[str, Any],
    evidence_audit: list[dict[str, Any]],
    *,
    root_hex: str,
    leaves_hex: list[str],
    fingerprint: str,
    issued_at: str,
) -> dict[str, Any]:
    """Assemble the signable manifest. ``issued_at`` is injected for determinism."""
    frameworks = [
        {
            "shortName": fw.get("shortName"),
            "framework": fw.get("framework"),
            "percentCompliant": fw.get("percentCompliant"),
            "controls": [
                {
                    "refCode": c.get("refCode"),
                    "status": c.get("status"),
                    "evidenceCount": c.get("evidenceCount", 0),
                }
                for c in fw.get("controls", [])
            ],
        }
        for fw in status.get("frameworks", [])
    ]
    return {
        "version": MANIFEST_VERSION,
        "org_id": org_id,
        "issued_at": issued_at,
        "summary": status.get("summary", {}),
        "frameworks": frameworks,
        "evidence": _evidence_records(evidence_audit),
        "merkle": {
            "algo": "sha256",
            "root": root_hex,
            "leaf_count": len(leaves_hex),
            "leaves": leaves_hex,
        },
        "key": {"alg": "Ed25519", "fingerprint": fingerprint},
    }

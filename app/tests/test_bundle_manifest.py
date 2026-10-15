"""Pure manifest/leaf tests (ADR-0016): canonicalisation determinism + leaf ordering."""

from __future__ import annotations

from app.api.bundle.manifest import build_leaves, build_manifest, canonical_bytes

_STATUS = {
    "frameworks": [
        {"shortName": "ISO-24113", "framework": "2023", "percentCompliant": 50.0, "controls": [
            {"refCode": "ISO 24113 §6.4", "status": "compliant", "evidenceCount": 1},
            {"refCode": "ISO 24113 §6.2", "status": "not_assessed", "evidenceCount": 0},
        ]},
    ],
    "summary": {"compliant": 1, "partial": 0, "not_assessed": 1, "total": 2, "percentCompliant": 50.0},
}

_AUDIT = [
    {"id": "01E", "displayID": "EV-1", "status": "READY", "controlRefs": ["ISO 24113 §6.4"],
     "audit": {"createdAt": "t0", "createdBy": "u", "updatedAt": "t1", "updatedBy": "u"}},
]


def test_canonical_bytes_is_sorted_and_compact() -> None:
    out = canonical_bytes({"b": 1, "a": 2})
    assert out == b'{"a":2,"b":1}'


def test_canonical_bytes_is_byte_stable() -> None:
    obj = {"z": [3, 2, 1], "a": {"y": 1, "x": 2}}
    assert canonical_bytes(obj) == canonical_bytes(dict(obj))


def test_build_leaves_orders_controls_then_evidence() -> None:
    leaves = build_leaves(_STATUS, _AUDIT)
    # 2 controls + 1 evidence record.
    assert len(leaves) == 3
    # Deterministic across calls.
    assert build_leaves(_STATUS, _AUDIT) == leaves


def test_build_manifest_embeds_root_and_leaf_count() -> None:
    leaves = build_leaves(_STATUS, _AUDIT)
    leaves_hex = [leaf.hex() for leaf in leaves]
    manifest = build_manifest(
        "01O", _STATUS, _AUDIT,
        root_hex="deadbeef", leaves_hex=leaves_hex, fingerprint="fp", issued_at="2026-06-07T00:00:00+00:00",
    )
    assert manifest["merkle"]["root"] == "deadbeef"
    assert manifest["merkle"]["leaf_count"] == 3
    assert manifest["version"] == "trust-bundle/v0"
    assert manifest["key"] == {"alg": "Ed25519", "fingerprint": "fp"}

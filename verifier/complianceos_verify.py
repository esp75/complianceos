#!/usr/bin/env python3
"""Offline verifier for ComplianceOS signed files. One file, no network, no ComplianceOS code.

Needs Python 3.10+ and the `cryptography` package (`pip install cryptography`).

    python complianceos_verify.py dossier-signed.json --fingerprint <hex>
    python complianceos_verify.py history.json --fingerprint <hex> [--previous earlier-history.json]

A signed file carries its own public key, so a signature alone proves the file is intact, not who
made it: anyone can sign a forged file with their own key. Get the signer's key fingerprint from
the operator through a channel you trust (not from the file) and pass it with --fingerprint.

Exit codes: 0 verified and signer pinned; 1 problems found; 2 intact but the signer is not pinned
(use --allow-unpinned to accept that knowingly)."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from typing import Any

DOSSIER_FORMAT = "complianceos-dossier/1"
HISTORY_FORMAT = "complianceos-program-history/1"


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _leaf(data: bytes) -> bytes:
    return hashlib.sha256(b"\x00" + data).digest()


def _node(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + left + right).digest()


def merkle_root(leaves: list[bytes]) -> bytes:
    if not leaves:
        return _leaf(b"")
    level = list(leaves)
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [_node(level[i], level[i + 1]) for i in range(0, len(level), 2)]
    return level[0]


def _check_signature(payload: bytes, doc: dict[str, Any], pinned: str | None) -> tuple[list[str], str]:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    problems: list[str] = []
    sig_hex, pub_hex = doc.get("signature_hex", ""), doc.get("public_key_hex", "")
    if not sig_hex or not pub_hex:
        return ["file is not signed"], ""
    try:
        pub_raw = bytes.fromhex(pub_hex)
        fingerprint = hashlib.sha256(pub_raw).hexdigest()
        if doc.get("fingerprint") not in (None, "", fingerprint):
            problems.append("stated fingerprint does not match the embedded public key")
        if pinned is not None and fingerprint != pinned.lower():
            problems.append(f"signed by key {fingerprint}, not the pinned {pinned.lower()}")
        try:
            Ed25519PublicKey.from_public_bytes(pub_raw).verify(bytes.fromhex(sig_hex), payload)
        except InvalidSignature:
            problems.append("signature does not verify: the file was changed or signed by another key")
    except ValueError:
        problems.append("signature or public key is malformed")
        return problems, ""
    return problems, fingerprint


def verify_dossier(doc: dict[str, Any], pinned: str | None) -> tuple[list[str], str]:
    problems: list[str] = []
    if doc.get("format") != DOSSIER_FORMAT:
        problems.append(f"unknown format {doc.get('format')!r}")
    payload = canonical({"format": doc.get("format"), "roadmap": doc.get("roadmap"),
                         "brief": doc.get("brief")})
    if doc.get("sha256") != hashlib.sha256(payload).hexdigest():
        problems.append("sha256 does not match the content")
    sig_problems, fp = _check_signature(payload, doc, pinned)
    return problems + sig_problems, fp


def verify_history(doc: dict[str, Any], pinned: str | None,
                   previous: dict[str, Any] | None = None) -> tuple[list[str], str]:
    problems: list[str] = []
    m = doc.get("manifest", {})
    if m.get("format") != HISTORY_FORMAT:
        problems.append(f"unknown format {m.get('format')!r}")
    events = m.get("events", [])
    if m.get("event_count") != len(events):
        problems.append("event_count does not match the events")
    if merkle_root([_leaf(canonical(e)) for e in events]).hex() != m.get("merkle_root"):
        problems.append("merkle_root does not match the events")
    if previous is not None:
        pm = previous.get("manifest", {})
        if m.get("previous_root") != pm.get("merkle_root"):
            problems.append("previous_root does not name the earlier file's merkle_root")
        old = {canonical(e) for e in pm.get("events", [])}
        if not old <= {canonical(e) for e in events}:
            problems.append("events recorded in the earlier file are missing from this one")
    sig_problems, fp = _check_signature(canonical(m), doc, pinned)
    return problems + sig_problems, fp


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verify a ComplianceOS signed dossier or history file.")
    ap.add_argument("file")
    ap.add_argument("--fingerprint", help="trusted signer key fingerprint (hex SHA-256 of the public key)")
    ap.add_argument("--previous", help="an earlier history export, to check the chain")
    ap.add_argument("--allow-unpinned", action="store_true")
    args = ap.parse_args(argv)

    with open(args.file, encoding="utf-8") as fh:
        doc = json.load(fh)
    if "manifest" in doc:
        previous = None
        if args.previous:
            with open(args.previous, encoding="utf-8") as fh:
                previous = json.load(fh)
        problems, fp = verify_history(doc, args.fingerprint, previous)
    else:
        problems, fp = verify_dossier(doc, args.fingerprint)

    if problems:
        print("NOT VERIFIED")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"Intact. Signed by key {fp}")
    if args.fingerprint is None:
        print("WARNING: signer not pinned. This shows the file is unchanged, not who made it.")
        return 0 if args.allow_unpinned else 2
    print("Signer matches the pinned fingerprint.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

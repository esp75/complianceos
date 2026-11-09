"""Signed program history (ADR-0021): the application event log as a tamper-evident export.

Every status change, update and contact entry of a workspace's applications is canonicalised, hashed
into a Merkle tree (the trust layer's ``merkle_root``), and the manifest is signed with the
workspace's Ed25519 key (the same key that signs the dossier). Each export names the previous
export's root, so a later export cannot silently drop what an earlier one recorded.

This module only *uses* the trust primitives; it does not modify trust-layer files. Verification
needs the JSON and the public key, nothing from the server."""

from __future__ import annotations

import datetime as dt
import json
from typing import Any

from pydantic import BaseModel

from app.api.trust.keys import key_fingerprint, public_raw
from app.api.trust.keystore import KeyStore, KeyStoreUnavailable
from app.api.trust.merkle import leaf_hash, merkle_root
from app.api.trust.signing import sign, verify
from app.planner.store import PlannerStore

FORMAT = "complianceos-program-history/1"


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


class HistoryDocument(BaseModel):
    """The signed export. ``signature_hex`` covers ``canonical(manifest)``."""

    manifest: dict[str, Any]
    signature_hex: str = ""
    public_key_hex: str = ""
    fingerprint: str = ""
    signed: bool = False
    note: str = ""


def _leaf(event: dict[str, Any]) -> bytes:
    return leaf_hash(canonical(event))


async def build_history(store: PlannerStore, workspace: str, keystore: KeyStore | None,
                        now: dt.datetime, mission_id: str | None = None) -> HistoryDocument:
    """Export (and checkpoint) the history of one workspace, or one of its missions."""
    missions = [m for m in await store.list_missions(workspace)
                if mission_id is None or m.id == mission_id]
    events: list[dict[str, Any]] = []
    for m in missions:
        for app in await store.list_applications(workspace, m.id):
            for e in await store.list_events(workspace, app.id):
                events.append({
                    "mission_id": m.id, "application_id": app.id, "license_id": app.license_id,
                    "event_id": e.id, "at": e.at.astimezone(dt.UTC).isoformat(), "kind": e.kind,
                    "from_status": e.from_status, "to_status": e.to_status, "note": e.note})
    events.sort(key=lambda e: (e["at"], e["application_id"], e["event_id"]))
    root = merkle_root([_leaf(e) for e in events]).hex()

    # Only a whole-workspace export joins the chain: a single mission's export is a view of part.
    prev = await store.last_history_root(workspace) if mission_id is None else None
    manifest = {"format": FORMAT, "workspace": workspace, "scope": mission_id or "workspace",
                "generated_at": now.astimezone(dt.UTC).isoformat(), "event_count": len(events),
                "merkle_root": root, "previous_root": prev, "events": events}

    doc = HistoryDocument(manifest=manifest, note="Unsigned: no signing key is configured.")
    if keystore is not None:
        try:
            priv = keystore.signing_key(f"workspace:{workspace}")
        except KeyStoreUnavailable:
            priv = None
        if priv is not None:
            pub = public_raw(priv)
            doc = HistoryDocument(manifest=manifest, signature_hex=sign(canonical(manifest), priv).hex(),
                                  public_key_hex=pub.hex(), fingerprint=key_fingerprint(pub),
                                  signed=True, note="Signed with this workspace's Ed25519 key.")
    if mission_id is None and doc.signed:
        await store.add_history_checkpoint(workspace, root, prev, len(events))
    return doc


def verify_history(doc: HistoryDocument, trusted_fingerprint: str | None = None) -> list[str]:
    """Problems found in an exported document; empty when it is internally consistent and signed
    correctly. Offline: uses only the document.

    The document carries its own public key, so a bare signature check proves integrity only, not
    origin: anyone can sign a forged history with their own key. Pass ``trusted_fingerprint``
    (obtained out of band, e.g. from the operator) to pin the signer; without it the result says
    nothing about who signed."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    problems: list[str] = []
    m = doc.manifest
    if m.get("format") != FORMAT:
        problems.append("unknown format")
    events = m.get("events", [])
    if m.get("event_count") != len(events):
        problems.append("event_count does not match the events")
    if merkle_root([_leaf(e) for e in events]).hex() != m.get("merkle_root"):
        problems.append("merkle_root does not match the events")
    if not doc.signed:
        problems.append("document is not signed")
    else:
        try:
            pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(doc.public_key_hex))
            if doc.fingerprint != key_fingerprint(bytes.fromhex(doc.public_key_hex)):
                problems.append("fingerprint does not match the embedded public key")
            if trusted_fingerprint is not None and doc.fingerprint != trusted_fingerprint:
                problems.append("signed by a different key than the trusted fingerprint")
            if not verify(canonical(m), bytes.fromhex(doc.signature_hex), pub):
                problems.append("signature does not verify")
        except ValueError:
            problems.append("signature or public key is malformed")
    return problems

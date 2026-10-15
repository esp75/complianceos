"""Pure detached-signature tests (ADR-0016): round-trip + rejection of tamper/wrong key."""

from __future__ import annotations

from app.api.trust.keys import derive_ed25519
from app.api.trust.signing import sign, verify

SEED = b"unit-test-master-seed-bytes-0001"


def test_sign_verify_roundtrip() -> None:
    key = derive_ed25519(SEED, "org-1")
    msg = b"canonical-manifest-bytes"
    sig = sign(msg, key)
    assert verify(msg, sig, key.public_key())


def test_verify_rejects_flipped_byte() -> None:
    key = derive_ed25519(SEED, "org-1")
    sig = sign(b"message", key)
    assert not verify(b"messagE", sig, key.public_key())


def test_verify_rejects_wrong_key() -> None:
    key = derive_ed25519(SEED, "org-1")
    other = derive_ed25519(SEED, "org-2")
    sig = sign(b"message", key)
    assert not verify(b"message", sig, other.public_key())

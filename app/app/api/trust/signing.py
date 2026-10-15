# MARKED-FOR-EXTERNAL-REVIEW — Trail of Bits / Quarkslab / Cure53
"""Detached Ed25519 signing of the canonical bundle manifest (Phase 4, ADR-0016).

Pure wrappers over pyca/cryptography. The signature covers ``canonical_bytes(manifest)`` and is
carried alongside the manifest in the bundle PDF, so any holder can re-verify offline with only the
org's public key (no master seed required).
"""

from __future__ import annotations

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


def sign(manifest_bytes: bytes, key: Ed25519PrivateKey) -> bytes:
    """Detached Ed25519 signature over the canonical manifest bytes."""
    return key.sign(manifest_bytes)


def verify(manifest_bytes: bytes, signature: bytes, pub: Ed25519PublicKey) -> bool:
    """True iff ``signature`` is a valid Ed25519 signature over ``manifest_bytes``."""
    try:
        pub.verify(signature, manifest_bytes)
    except InvalidSignature:
        return False
    return True

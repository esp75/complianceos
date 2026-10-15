# MARKED-FOR-EXTERNAL-REVIEW — Trail of Bits / Quarkslab / Cure53
"""Per-Organization Ed25519 key derivation (Phase 4, ADR-0016).

Keys are *derived*, never stored: each org's keypair comes from a single master seed via
HKDF-SHA256 with the org_id as the HKDF ``info``. Pure functions, no I/O — the only secret is the
master seed, supplied by the caller (env-only ``CELESTIA_TRUST_SIGNING_SEED`` in v0; an EU KMS
behind the KeyStore interface later). HKDF is one-way, so a derived org key never reveals the seed
or another org's key.
"""

from __future__ import annotations

import hashlib

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

# Fixed, versioned salt. Bump the suffix to rotate every org's derived key in lockstep (ADR-0016).
_HKDF_SALT = b"celestia-trust-v0"


def derive_ed25519(master_seed: bytes, org_id: str) -> Ed25519PrivateKey:
    """Deterministically derive an org's Ed25519 private key from the master seed.

    Same ``(master_seed, org_id)`` always yields the same key (offline + test-deterministic).
    """
    if not master_seed:
        raise ValueError("master_seed is empty; set CELESTIA_TRUST_SIGNING_SEED")
    seed = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_HKDF_SALT,
        info=org_id.encode("utf-8"),
    ).derive(master_seed)
    return Ed25519PrivateKey.from_private_bytes(seed)


def public_raw(priv: Ed25519PrivateKey) -> bytes:
    """The 32-byte raw Ed25519 public key (the publishable verification material)."""
    from cryptography.hazmat.primitives import serialization

    return priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def key_fingerprint(pub_raw: bytes) -> str:
    """Hex SHA-256 of the raw public key — a stable, shareable key identifier."""
    return hashlib.sha256(pub_raw).hexdigest()

# MARKED-FOR-EXTERNAL-REVIEW — Trail of Bits / Quarkslab / Cure53
"""KeyStore interface + v0 derived implementation (Phase 4, ADR-0016).

The interface is the swap seam: v0 derives per-org keys from a master seed (offline, deterministic),
production swaps in an EU KMS/HSM-backed store without touching callers. ``DerivedKeyStore`` raises
``KeyStoreUnavailable`` when no master seed is configured so the endpoint can 503 cleanly rather than
sign with a degenerate key.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from app.api.trust.keys import derive_ed25519, key_fingerprint, public_raw


class KeyStoreUnavailable(RuntimeError):
    """Raised when no signing material is configured (e.g. master seed unset)."""


@runtime_checkable
class KeyStore(Protocol):
    def signing_key(self, org_id: str) -> Ed25519PrivateKey: ...
    def public_key(self, org_id: str) -> Ed25519PublicKey: ...
    def fingerprint(self, org_id: str) -> str: ...


class DerivedKeyStore:
    """v0 KeyStore: HKDF-derives each org's Ed25519 key from a master seed."""

    def __init__(self, master_seed: bytes) -> None:
        self._seed = master_seed

    @property
    def available(self) -> bool:
        return bool(self._seed)

    def signing_key(self, org_id: str) -> Ed25519PrivateKey:
        if not self._seed:
            raise KeyStoreUnavailable("trust signing seed not configured")
        return derive_ed25519(self._seed, org_id)

    def public_key(self, org_id: str) -> Ed25519PublicKey:
        return self.signing_key(org_id).public_key()

    def fingerprint(self, org_id: str) -> str:
        return key_fingerprint(public_raw(self.signing_key(org_id)))

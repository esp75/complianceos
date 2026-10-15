"""Pure key-derivation tests (ADR-0016): determinism, per-org/per-seed isolation, fingerprint."""

from __future__ import annotations

from app.api.trust.keys import derive_ed25519, key_fingerprint, public_raw

SEED = b"unit-test-master-seed-bytes-0001"


def test_derivation_is_deterministic() -> None:
    a = public_raw(derive_ed25519(SEED, "org-1"))
    b = public_raw(derive_ed25519(SEED, "org-1"))
    assert a == b


def test_different_org_gives_different_key() -> None:
    a = public_raw(derive_ed25519(SEED, "org-1"))
    b = public_raw(derive_ed25519(SEED, "org-2"))
    assert a != b


def test_different_seed_gives_different_key() -> None:
    a = public_raw(derive_ed25519(SEED, "org-1"))
    b = public_raw(derive_ed25519(b"another-master-seed-bytes-000002", "org-1"))
    assert a != b


def test_fingerprint_is_sha256_hex_of_pubkey() -> None:
    pub = public_raw(derive_ed25519(SEED, "org-1"))
    fp = key_fingerprint(pub)
    assert len(fp) == 64
    assert all(c in "0123456789abcdef" for c in fp)


def test_empty_seed_rejected() -> None:
    try:
        derive_ed25519(b"", "org-1")
    except ValueError:
        return
    raise AssertionError("expected ValueError on empty seed")

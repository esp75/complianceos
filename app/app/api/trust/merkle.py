# MARKED-FOR-EXTERNAL-REVIEW — Trail of Bits / Quarkslab / Cure53
"""SHA-256 Merkle tree for the evidence/control leaf set (Phase 4, ADR-0016).

Pure, no I/O. Domain-separated hashing (0x00 prefix for leaves, 0x01 for internal nodes) so a leaf
value can never be reinterpreted as an internal node (second-preimage defence). Odd levels promote
the last node by duplicating it (the common "duplicate-last" convention). The Merkle root seals the
bundle's contents; ``inclusion_proof``/``verify_inclusion`` let a regulator prove a single evidence
record is in the bundle without revealing the rest.
"""

from __future__ import annotations

import hashlib

_LEAF = b"\x00"
_NODE = b"\x01"


def leaf_hash(data: bytes) -> bytes:
    """Hash of a leaf payload (domain-separated)."""
    return hashlib.sha256(_LEAF + data).digest()


def node_hash(left: bytes, right: bytes) -> bytes:
    """Hash of an internal node from its two child hashes (domain-separated)."""
    return hashlib.sha256(_NODE + left + right).digest()


def merkle_root(leaves: list[bytes]) -> bytes:
    """Root over an ordered list of leaf hashes (output of ``leaf_hash``).

    Empty input hashes the empty leaf so a root always exists.
    """
    if not leaves:
        return leaf_hash(b"")
    level = list(leaves)
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])  # duplicate-last for odd width
        level = [node_hash(level[i], level[i + 1]) for i in range(0, len(level), 2)]
    return level[0]


def inclusion_proof(leaves: list[bytes], index: int) -> list[tuple[bytes, bool]]:
    """Audit path for ``leaves[index]``: list of (sibling_hash, sibling_is_right).

    Replaying it with ``verify_inclusion`` reconstructs the root.
    """
    if not 0 <= index < len(leaves):
        raise IndexError("leaf index out of range")
    proof: list[tuple[bytes, bool]] = []
    level = list(leaves)
    idx = index
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        if idx % 2:
            proof.append((level[idx - 1], False))  # sibling on the left
        else:
            proof.append((level[idx + 1], True))   # sibling on the right
        level = [node_hash(level[i], level[i + 1]) for i in range(0, len(level), 2)]
        idx //= 2
    return proof


def verify_inclusion(leaf: bytes, proof: list[tuple[bytes, bool]], root: bytes) -> bool:
    """True iff replaying ``proof`` from ``leaf`` reproduces ``root``."""
    acc = leaf
    for sibling, sibling_is_right in proof:
        acc = node_hash(acc, sibling) if sibling_is_right else node_hash(sibling, acc)
    return acc == root

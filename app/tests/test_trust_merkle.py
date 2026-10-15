"""Pure Merkle tests (ADR-0016): root construction, inclusion proofs, domain separation."""

from __future__ import annotations

from app.api.trust.merkle import (
    inclusion_proof,
    leaf_hash,
    merkle_root,
    node_hash,
    verify_inclusion,
)


def _leaves(n: int) -> list[bytes]:
    return [leaf_hash(f"leaf-{i}".encode()) for i in range(n)]


def test_single_leaf_root_is_the_leaf() -> None:
    a = leaf_hash(b"only")
    assert merkle_root([a]) == a


def test_two_leaf_root_is_node_of_both() -> None:
    a, b = _leaves(2)
    assert merkle_root([a, b]) == node_hash(a, b)


def test_three_leaf_root_duplicates_last() -> None:
    a, b, c = _leaves(3)
    assert merkle_root([a, b, c]) == node_hash(node_hash(a, b), node_hash(c, c))


def test_four_leaf_root_is_balanced() -> None:
    a, b, c, d = _leaves(4)
    assert merkle_root([a, b, c, d]) == node_hash(node_hash(a, b), node_hash(c, d))


def test_inclusion_proof_verifies_every_index() -> None:
    leaves = _leaves(5)
    root = merkle_root(leaves)
    for i, leaf in enumerate(leaves):
        proof = inclusion_proof(leaves, i)
        assert verify_inclusion(leaf, proof, root)


def test_inclusion_proof_rejects_tampered_leaf() -> None:
    leaves = _leaves(4)
    root = merkle_root(leaves)
    proof = inclusion_proof(leaves, 1)
    assert not verify_inclusion(leaf_hash(b"tampered"), proof, root)


def test_inclusion_proof_rejects_wrong_root() -> None:
    leaves = _leaves(4)
    proof = inclusion_proof(leaves, 0)
    assert not verify_inclusion(leaves[0], proof, leaf_hash(b"not-the-root"))


def test_domain_separation_leaf_ne_node() -> None:
    a, b = _leaves(2)
    # A leaf whose payload equals a node's child concatenation must not collide with that node.
    assert leaf_hash(a + b) != node_hash(a, b)

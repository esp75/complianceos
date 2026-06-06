"""Unit tests for the deterministic v0 embedding (ADR-0014)."""

from __future__ import annotations

import math

from app.kg.embeddings import EMBEDDING_DIM, HashingEmbedding, to_pgvector


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def test_deterministic_and_correct_dim() -> None:
    emb = HashingEmbedding()
    v1 = emb.embed("post-mission disposal of the spacecraft")
    v2 = emb.embed("post-mission disposal of the spacecraft")
    assert v1 == v2
    assert len(v1) == EMBEDDING_DIM == 384


def test_unit_normalized() -> None:
    v = HashingEmbedding().embed("collision avoidance manoeuvre")
    assert math.isclose(math.sqrt(sum(x * x for x in v)), 1.0, abs_tol=1e-9)


def test_related_text_scores_higher_than_unrelated() -> None:
    emb = HashingEmbedding()
    query = emb.embed("how is post-mission disposal evidenced")
    disposal = emb.embed("the operator shall execute post-mission disposal and evidence it")
    filing = emb.embed("ITU advance publication information filing for an orbital slot")
    assert _cosine(query, disposal) > _cosine(query, filing)


def test_empty_text_is_safe() -> None:
    v = HashingEmbedding().embed("")
    assert len(v) == EMBEDDING_DIM
    assert all(x == 0.0 for x in v)  # no tokens -> zero vector (norm guarded)


def test_to_pgvector_format() -> None:
    assert to_pgvector([1.0, 0.0, -0.5]) == "[1.0,0.0,-0.5]"

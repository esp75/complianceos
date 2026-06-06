"""Embedding providers for the L2 vector index (ADR-0004 local level).

v0 (ADR-0014) ships a deterministic, dependency-free hashing embedding so the slice runs
offline and sovereign-by-construction (nothing leaves the box). Dim 384 is forward-compatible
with BAAI/bge-small / bge-m3 — the production model slots in behind the same Protocol.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol, runtime_checkable

EMBEDDING_DIM = 384

_TOKEN_RE = re.compile(r"[a-z0-9]+")


@runtime_checkable
class EmbeddingProvider(Protocol):
    @property
    def dim(self) -> int: ...

    def embed(self, text: str) -> list[float]: ...


def _tokens(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if len(t) > 2]


class HashingEmbedding:
    """Signed feature-hashing bag-of-words embedding, L2-normalized.

    Cosine similarity between two texts ≈ their normalized shared-term overlap — enough to
    surface related obligations for the DoD. Deterministic: same text → same vector.
    """

    def __init__(self, dim: int = EMBEDDING_DIM) -> None:
        self._dim = dim

    @property
    def dim(self) -> int:
        return self._dim

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self._dim
        for tok in _tokens(text):
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)  # noqa: S324 - non-crypto use
            idx = h % self._dim
            sign = 1.0 if (h >> 8) & 1 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


def to_pgvector(embedding: list[float]) -> str:
    """Format a vector as a pgvector literal, e.g. '[0.1,0.2,...]'."""
    return "[" + ",".join(repr(round(v, 6)) for v in embedding) + "]"

"""L4 dual-level retrieval — the LightRAG pattern over Postgres (ADR-0004).

- Local level: pgvector ANN on the query embedding.
- Global level: AGE CITES traversal from the local hits, hydrated from the vector table.
- Fusion: local hits ranked by vector score, graph-expanded neighbors appended below.

The reranker (bge-reranker-v2-m3) is deferred (ADR-0014); fusion here is a simple score
ordering. Returns the obligations to cite plus the evidence types they require.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.clients.kg import KGClient
from app.kg.embeddings import EmbeddingProvider

_GLOBAL_SCORE = 0.4  # fixed score for graph-expanded neighbors (below any vector match)


class RetrievedObligation(BaseModel):
    ref_code: str
    framework: str
    content: str
    score: float
    level: str  # "local" (vector) | "global" (graph)


class RetrievalResult(BaseModel):
    obligations: list[RetrievedObligation] = Field(default_factory=list)
    evidence_types: list[str] = Field(default_factory=list)


async def retrieve(
    kg: KGClient, embed: EmbeddingProvider, query: str, *, k: int = 3
) -> RetrievalResult:
    # Local: vector ANN.
    hits = await kg.search_obligations(embed.embed(query), k)
    local = [
        RetrievedObligation(
            ref_code=h["ref_code"], framework=h["framework"], content=h["content"],
            score=round(1.0 - float(h["distance"]), 4), level="local",
        )
        for h in hits
    ]
    local_refs = [o.ref_code for o in local]

    # Global: CITES-neighbors of the local hits, excluding ones already retrieved locally.
    neighbor_refs = [r for r in await kg.cited_neighbors(local_refs) if r not in local_refs]
    neighbors = [
        RetrievedObligation(
            ref_code=row["ref_code"], framework=row["framework"], content=row["content"],
            score=_GLOBAL_SCORE, level="global",
        )
        for row in await kg.fetch_obligations(neighbor_refs)
    ]

    obligations = local + neighbors
    all_refs = [o.ref_code for o in obligations]
    evidence_types = sorted(set(await kg.evidence_types_for(all_refs)))
    return RetrievalResult(obligations=obligations, evidence_types=evidence_types)

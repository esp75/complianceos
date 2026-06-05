# ADR 0004 — LightRAG dual-level retrieval pattern over Postgres + AGE + pgvector

**Status**: Accepted — 2026-05-15
**Decision-makers**: Maxime Kadr (solo)

## Context

L4 (drafting agent) needs citation-grounded RAG over the L2 regulatory knowledge graph. Regulators will not accept hallucinated obligations; every drafted compliance statement must cite a specific provision in the L2 graph.

**HKUDS/LightRAG** (MIT, 35k+ stars, EMNLP 2025) is the strongest published retrieval architecture for this use case: a dual-level retrieval system combining vector similarity (pgvector) with knowledge-graph entity/relationship traversal (Apache AGE), with a reranker stage, and published reproducible benchmarks vs NaiveRAG and Microsoft GraphRAG.

LightRAG ships with its own storage layer (its own KG and vector store). v0.1 already commits to Postgres 17 + Apache AGE + pgvector as the production KG store, for EU-sovereignty and multi-tenancy-via-RLS reasons.

## Decision

Adopt LightRAG's **retrieval algorithm and architecture as a pattern**. Re-implement it against the existing Postgres + AGE + pgvector substrate. Do NOT vendor LightRAG's storage layer.

Concretely:
- L4 retrieval module lives at `layers/L4-drafting-agent/retrieval/`.
- Implements the LightRAG dual-level algorithm:
  - **Local retrieval**: pgvector ANN on chunk embeddings.
  - **Global retrieval**: AGE Cypher traversal from entity matches outward.
  - **Mixed mode**: hybrid scoring with reranker (BAAI/bge-reranker-v2-m3, run on EU-hosted inference).
- Vendor LightRAG at SHA `405525a5e5b2c7d4385a0a3d4726accd285f9934` for **reference reading** only — copy patterns, do not import code.

## Consequences

**Positive**
- One storage substrate (Postgres + AGE + pgvector) for L2 KG + L4 retrieval. No sync nightmare between two graph stores.
- EU sovereignty preserved (no Cassandra, no Qdrant, no third-party-hosted retrieval).
- Re-implementation discipline forces us to understand the algorithm rather than treating it as a black box — useful when regulators ask how citation grounding works.
- pgvector + AGE composability already proven in v0.1 plan.

**Negative**
- Implementation cost: ~2–3 weeks to port LightRAG's dual-level retriever to the Postgres stack. Mitigated by the cherry-picked `rag-architect` skill in `.claude/skills/`.
- Diverges from upstream LightRAG; no automatic upstream improvements.
- Reranker model (BAAI/bge-reranker-v2-m3) is BAAI-released, weights hosted on HuggingFace. Verify EU-hosted inference availability or mirror weights internally.

**EU sovereignty check**
- All retrieval state stays in Postgres on Hetzner. Reranker inference must run on EU endpoints (verify before Phase 3).

## Alternatives considered

- **Vendor LightRAG runtime** — introduces a second graph store; conflicts with v0.1's Postgres-only commitment. Rejected.
- **Microsoft GraphRAG** — LightRAG benchmarks comparable retrieval quality with better diversity scores. Rejected on parity grounds.
- **Naive RAG (pgvector only, no graph)** — fails LightRAG's reproducible benchmark by ~35 points; insufficient citation grounding. Rejected.

## Open questions

- Whether to use Apache AGE's Cypher or write graph traversal as recursive CTEs. Default to AGE Cypher in Phase 3; benchmark.
- Embedding model: `text-embedding-3-large` (OpenAI, US) vs `BAAI/bge-m3` (open weights, EU-hostable). Default to bge-m3 for sovereignty.

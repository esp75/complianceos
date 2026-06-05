# L4 — Drafting Agent

Citation-grounded compliance drafting with provenance. See ADRs [0004](../../adr/0004-lightrag-pattern-over-postgres-age-pgvector.md), [0005](../../adr/0005-trustgraph-context-cores-pattern-only.md), [0006](../../adr/0006-compliancenlp-architecture-for-l2-l4.md).

## Role

Produce regulator-defensible compliance drafts, gap analyses, and audit responses. Every output cites specific L2 obligations + L1 evidence records + L3 numbers. Hallucinations are a fail-state, not a tolerable noise floor.

## Architecture summary

- **Retrieval** (`retrieval/`) — LightRAG dual-level pattern (local vector + global graph + reranker) over Postgres pgvector + AGE Cypher. Re-implemented; not vendored.
- **Extraction** (`extraction/`) — ComplianceNLP three-head pipeline (NER, modality, cross-ref). Shares the L2 extractor codebase.
- **Provenance** (`provenance/`) — Context Core schema from trustgraph + PROV-O pattern. Postgres tables + AGE edges recording source, time, derivation, evidence chain.
- **Drafting** (`drafting/`) — prompt templates + tool-using agent. EU-jurisdiction LLM endpoints (Anthropic EU, Mistral). Output: PAdES-signed PDF + structured JSON.

## Trust boundary

L4 drafting code lives in `app/api/trust/draft/**` (future). Files marked `# MARKED-FOR-EXTERNAL-REVIEW`. Off-limits to `/codex` (US jurisdiction).

## Sub-folders

- `retrieval/` — LightRAG-pattern dual-level retriever (vector + graph + rerank)
- `extraction/` — three-head LEGAL-BERT pipeline (shared with L2)
- `provenance/` — Context Core schema + Postgres tables + AGE edges
- `drafting/` — prompt templates + agent orchestration + PAdES PDF emit

## Phase 3 deliverables (see ROADMAP.md)

- [ ] Dual-level retriever: local pgvector ANN + global AGE Cypher + bge-reranker-v2-m3
- [ ] Provenance tables + edges; every retrieved chunk has a source manifest
- [ ] Drafting agent v0: obligation Q → 1-paragraph compliance assertion with ≥2 obligation citations + ≥1 evidence citation
- [ ] Citation enforcer: any unsupported claim fails validation and never reaches output
- [ ] Held-out eval: retrieval P@5 ≥ 0.8 on a Celestia-built test set; drafting coverage ≥ 90%

## Skills to invoke

- `rag-architect` — primary skill for retrieval design
- `prompt-engineer` — drafting prompt template design
- `claude-api` skill (gstack) — for Anthropic SDK integration with prompt caching enabled
- `/cso` — on every PR touching `app/api/trust/draft/**`

## Upstream reference

- LightRAG: `external/lightrag/` at SHA `405525a5e5b2c7d4385a0a3d4726accd285f9934` (pattern read only)
- trustgraph: `external/trustgraph/` at SHA `159b1e282406810b4a10e109d444b5ac85941b96` (Context Cores schema only)
- ComplianceNLP: `external/compliance-nlp/` at SHA `8a85f38aef6720eeeb7e25ba97b91f5e55f3ca3b`

## Open questions

- Reranker hosting: BAAI/bge-reranker-v2-m3 weights on HuggingFace. Mirror to EU storage; consider Hetzner GPU inference vs Hugging Face Inference EU endpoint.
- Prompt caching strategy for drafting: per-Organization, per-Framework, or both. Default: both, with cache-control hints around the static-per-org and static-per-framework system prompt segments.
- LLM endpoint failover: if Anthropic EU unavailable, fall back to Mistral; never fall back to US-hosted endpoints automatically. Document in `THREAT_MODEL.md`.

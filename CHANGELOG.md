# Changelog

All notable changes to ComplianceOS are documented here. Format: [Keep a Changelog](https://keepachangelog.com/).

## [0.2.0] — 2026-05-15 — "Stand on Giants"

Strategic shift from "build everything" (v0.1) to "fork three Apache-2.0 substrates and add the space-specific layer on top."

### Added
- 9 vendored upstream dependencies under `external/` with pinned SHAs (theopenlane/core, Orekit, OSTk, openmct, LightRAG, trustgraph, ComplianceNLP, accord-nlp, ITU-Compliance-Assessment-Monitor)
- 8 cherry-picked Jeffallan claude-skills under `.claude/skills/` (RAG Architect, Prompt Engineer, Postgres Pro, Database Optimizer, MCP Developer, FastAPI Expert, Next.js Developer, Kubernetes Specialist)
- 9 Architecture Decision Records (`adr/0001` through `adr/0009`)
- Layer-scoped sub-projects: `layers/L1-substrate/`, `L2-knowledge-graph/`, `L3-sder-engine/`, `L4-drafting-agent/`, `L5-dashboard/`, `cross-cutting/`
- gbrain-ingested architecture pages (Overview, L1–L5, each ADR)
- License matrix and dependency map under `docs/`

### Changed
- L1 build path: "build evidence vault + audit log + RBAC + SSO" → "fork theopenlane/core, model space frameworks as Openlane Frameworks"
- L3 orbital math path: "build custom propagation" → "Orekit JVM microservice (ESA/CNES governance) for defensible numbers, OSTk Python for exploration"
- L5 dashboard direction: "Next.js custom dashboard" → "openmct (NASA Ames) plugin host for operator views; Next.js retained for insurer/regulator portals" (see ADR-0003)
- L2 KG store: gbrain MCP retained as **agent memory only**; production KG remains Postgres 17 + Apache AGE + pgvector per v0.1's EU sovereignty rules (see ADR-0007)
- L4 retrieval: re-implement LightRAG's dual-level retrieval pattern over Postgres+AGE+pgvector (NOT vendor LightRAG storage)

### Removed
- trustgraph as a runtime (Cassandra+Pulsar+Qdrant incompatible with EU-sovereign Postgres-only constraint) — pattern adoption only (Context Cores provenance schema)

### Decisions locked 2026-05-15
- ADR-0010: MVP LLM policy = Claude only (Anthropic EU endpoint). Mistral deferred post-MVP.
- ADR-0011: External security review vendor = Quarkslab (FR) primary, Cure53 (DE) backup. Trail of Bits dropped.

### Carried over from v0.1
- EU-sovereign infrastructure rules (Hetzner, no US-hosted prod data)
- Trust-layer external-review convention (`MARKED-FOR-EXTERNAL-REVIEW` header)
- Postgres 17 + Apache AGE + pgvector + FastAPI + Next.js 14 stack
- Ed25519 signing + Merkle audit chain + signed PAdES bundles

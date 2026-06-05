# ADR 0005 — trustgraph Context Cores pattern only (no runtime adoption)

**Status**: Accepted — 2026-05-15
**Decision-makers**: Maxime Kadr (solo)
**Reverses earlier recommendation**: the initial resource assessment recommended "Vendor trustgraph as L4 agent runtime." The v0.1 EU-sovereignty + Postgres-only constraints make that infeasible.

## Context

**trustgraph-ai/trustgraph** (Apache-2.0, 2,079 stars) is a multi-agent orchestration runtime with Document/Graph/Ontology RAG and a notable feature: **Context Cores** — formal source manifests + provenance tracking (where facts came from, when, how derived). This is exactly what Celestia's L4 needs for citation grounding.

The catch: trustgraph's runtime depends on Apache Cassandra (storage), Apache Pulsar (message bus), and Qdrant (vectors). These are operationally heavy and conflict with v0.1's Postgres-only EU-sovereign deployment plan.

## Decision

Adopt **only the Context Cores schema and provenance pattern** from trustgraph. Re-implement against Postgres + AGE.

- Vendor trustgraph at SHA `159b1e282406810b4a10e109d444b5ac85941b96` for **reference reading** only.
- Provenance schema lives at `layers/L4-drafting-agent/provenance/` — patterned after trustgraph's Context Cores (source, time, derivation method, evidence chain).
- Also fold in PROV-O pattern from VeritasGraph (license unclear; pattern only, no code).
- Do NOT deploy Cassandra, Pulsar, or Qdrant. Do NOT introduce trustgraph as a runtime.

## Consequences

**Positive**
- Citation grounding gains a formal provenance ontology compatible with PROV-O. Defensible to regulators who ask "where did this claim come from?"
- Single storage substrate preserved (Postgres + AGE + pgvector).
- No heavy infra ops added.

**Negative**
- Re-implementation cost: ~1 week to port Context Core schema to Postgres tables and AGE edges.
- No automatic upstream improvements from trustgraph.

**EU sovereignty check**
- Pattern adoption only. No runtime, no upstream services. ✓ compatible.

## Alternatives considered

- **Adopt trustgraph runtime in parallel with Postgres** — two graph stores, sync nightmare, Cassandra+Pulsar ops cost in EU deployment. Rejected.
- **Replace gbrain + Postgres with trustgraph** — violates v0.1 EU-sovereignty and Postgres-RLS multi-tenancy commitment. Rejected.
- **Skip provenance ontology, rely on free-text citations** — fails the regulator-defensibility bar. Rejected.

## Open questions

- Exact Context Core fields to port — see Phase 3 implementation.
- Whether to expose provenance via a SPARQL endpoint (trustgraph offers this) for regulator-side querying. Default: no — expose via GraphQL through theopenlane.

# ADR 0007 — Postgres 17 + Apache AGE + pgvector as production KG substrate; gbrain only for agent memory

**Status**: Accepted — 2026-05-15 (carried from v0.1)
**Decision-makers**: Maxime Kadr (solo)
**Clarifies**: where gbrain MCP sits relative to production KG

## Context

The resource assessment initially evaluated gbrain MCP as a candidate L2 production KG substrate. v0.1 had already committed to Postgres 17 + Apache AGE + pgvector for production data, for three reasons:

1. **EU sovereignty**: managed Postgres on Hetzner is straightforward; Neo4j/Cassandra/Qdrant SaaS offerings are US-jurisdiction.
2. **Multi-tenancy**: Postgres Row-Level Security (RLS) provides operator/insurer/regulator data partitioning that none of the graph-native alternatives match natively.
3. **Audit trail**: a single substrate for all production data means the Merkle audit chain has one source of truth.

gbrain is the Claude agent's knowledge graph (PGLite-backed). It is local to the developer's machine, not production infrastructure.

## Decision

- **Production KG**: Postgres 17 + Apache AGE (graph) + pgvector (vector). Single substrate for L2 obligations, L4 retrieval state, evidence vault metadata, and audit log.
- **Agent memory**: gbrain stays local to the developer machine, used to model the architecture for Claude sessions, ingest documentation, and accelerate code navigation. Never touches production data.
- **No second production graph store.** No Neo4j, no Cassandra, no Qdrant, no Pulsar. (See ADRs 0004 and 0005 for the related "pattern only, no runtime" decisions.)

## Consequences

**Positive**
- One substrate, one backup story, one RLS policy, one Merkle chain.
- Hetzner-managed Postgres = EU sovereignty fully satisfied.
- AGE is open-source (Apache-2.0) and AGE-on-Hetzner is a known deployment shape.
- pgvector now in mainline Postgres ecosystem; mature.

**Negative**
- AGE is younger than Neo4j; some operational gaps (e.g., fewer dashboarding tools).
- Multi-graph queries can be slower than native graph DBs — mitigated by careful schema and pgvector hybrid retrieval.

**EU sovereignty check**
- Hetzner managed Postgres in DE. ✓ fully compatible.

## Alternatives considered

- gbrain as production substrate — rejected; PGLite is single-user agent memory, not multi-tenant production.
- Neo4j community edition — GPL3, contaminates closed-source distribution. Rejected.
- Cassandra/Qdrant/Pulsar (trustgraph runtime) — see ADR-0005. Rejected on infra cost + sovereignty.

## Open questions

- AGE version pinning policy — track upstream releases monthly.
- pgvector + AGE hybrid query optimizer hints — empirically tune in Phase 3.

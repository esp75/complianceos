# Dependency Map

Where each Celestia source path depends on which upstream code.

```
layers/L1-substrate/
    extensions/                  -> consumes external/theopenlane-core via GraphQL
    frameworks/eu-space-act/     -> Openlane Framework YAML/JSON definitions
    frameworks/iso-24113/        -> same
    frameworks/itu/              -> same

layers/L2-knowledge-graph/
    extractors/                  -> patterns from external/compliance-nlp + external/accord-nlp
    ontology/                    -> RASE schema from external/accord-nlp
    corpus/                      -> Celestia-original; annotated against EU Space Act + ISO 24113 + ITU
    ingest/                      -> Celestia-original; pushes to AGE/pgvector

layers/L3-sder-engine/
    orekit-service/              -> wraps external/orekit (Java 21, Spring Boot, gRPC)
    ostk-explore/                -> imports external/ostk Python bindings
    itu-compliance/              -> port of external/itu-compliance-monitor (Python)
    risk-scoring/                -> Celestia-original; consumes orekit-service + itu-compliance

layers/L4-drafting-agent/
    retrieval/                   -> pattern from external/lightrag; implemented over Postgres+AGE+pgvector
    extraction/                  -> shares codebase with layers/L2-knowledge-graph/extractors/
    provenance/                  -> pattern from external/trustgraph (Context Cores) + PROV-O
    drafting/                    -> Celestia-original; calls EU-jurisdiction LLM endpoints

layers/L5-dashboard/
    openmct-host/                -> wraps external/openmct (Vue 3); see ADR-0003
    plugins/                     -> Celestia-original Vue 3 plugins
    apps/portal/  (future)       -> Next.js 14 + shadcn/ui

layers/cross-cutting/
    auth/                        -> OpenFGA model + theopenlane/core auth surface
    observability/               -> Prometheus + Grafana + Loki
    deploy/                      -> docker-compose + Coolify config

.claude/skills/
    rag-architect/               -> ext/jeffallan-skills/skills/rag-architect (MIT, copied)
    prompt-engineer/             -> same
    postgres-pro/                -> same
    database-optimizer/          -> same
    mcp-developer/               -> same
    fastapi-expert/              -> same
    nextjs-developer/            -> same
    kubernetes-specialist/       -> same
```

## Layer ↔ ADR mapping

| Layer | Governed by ADRs |
|---|---|
| L1 substrate | 0001, 0007 |
| L2 knowledge graph | 0006, 0007, 0008 |
| L3 SDER engine | 0002, 0009 |
| L4 drafting agent | 0004, 0005, 0006 |
| L5 dashboards | 0003 |
| Cross-cutting | 0001 (auth), 0007 (storage) |

## Versioning policy

- Vendored upstream SHAs pinned in `external/VENDOR.md`.
- Celestia source paths target the pinned SHAs only. Never `external/*/HEAD`.
- ADR required to bump any vendored SHA.
- Celestia `VERSION` (semver) bumps with each Phase milestone: 0.2.0 (now) → 0.3.0 (Phase 1) → ... → 1.0.0 (post-Phase 5 external audit).

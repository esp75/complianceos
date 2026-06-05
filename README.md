# ComplianceOS v0.2 — Celestia Dynamics

**EU-sovereign regulatory compliance SaaS for satellite operators, insurers, and regulators.**

This repo is the v0.2 evolution of [complianceOS v0.1](../complianceOS/). The shift: from "build everything" to "stand on three Apache-2.0 substrates and add the space-specific layer on top."

## Why v0.2

A deep due-diligence review (see `docs/resource-assessment.md`) of 28 candidate OSS dependencies identified three high-leverage substrates that collapse months of foundational build into weeks of integration:

1. **theopenlane/core** (Apache-2.0) — evidence vault + audit log + OpenFGA RBAC + SSO + GraphQL + questionnaire engine. Replaces L1 build from scratch.
2. **CS-SI/Orekit** (Apache-2.0) — ESA/CNES/NRL/Airbus PMC-governed orbital mechanics. Defensible numbers for insurers and regulators.
3. **NASA Ames openmct** (Apache-2.0) — mission-control dashboard framework. Operators get the idiom they expect; regulators inherit NASA brand association.

Plus pattern adoption from LightRAG (EMNLP-2025 dual-level retrieval), ComplianceNLP (Apr-2026 KG-augmented RAG with LEGAL-BERT heads), trustgraph (Context Core provenance), accord-nlp (RASE annotation), and ITU-Compliance-Assessment-Monitor (SNL parser + filing-maturity state machine).

## Architecture (5 layers + cross-cutting)

| Layer | Substrate | Purpose |
|---|---|---|
| **L1 — Substrate** | theopenlane/core fork | Evidence vault, audit log, RBAC, SSO, controls, GraphQL API |
| **L2 — Knowledge Graph** | Postgres 17 + Apache AGE + pgvector | EU Space Act, ISO 24113, ITU obligations as code |
| **L3 — SDER Engine** | Orekit (JVM service) + OSTk (Python) + ITU port | Orbital mechanics, conjunction, ITU compliance, debris, insurer risk scoring |
| **L4 — Drafting Agent** | LightRAG pattern + ComplianceNLP architecture | Citation-grounded RAG with PROV-O provenance |
| **L5 — Dashboard** | openmct (operators) + Next.js 14 (insurers/regulators) | Mission-control UI + portal UI |
| **Cross-cutting** | OpenFGA, Hetzner, Coolify | Multi-tenant auth, EU-sovereign deploy, observability |

See [`ARCHITECTURE.md`](./ARCHITECTURE.md) for full diagrams and data flow.

## Status

**Scaffolding phase.** Not yet a functioning system. See [`STATUS.md`](./STATUS.md) for what is and isn't built.

## License

Apache-2.0 — compatible with every vendored upstream. See [`LICENSE`](./LICENSE) and [`docs/license-matrix.md`](./docs/license-matrix.md).

## EU sovereignty

All production data and identity stay on EU infrastructure (Hetzner DE). No US-hosted services for application data. See [`CLAUDE.md`](./CLAUDE.md) for the full rules.

# Decisions (ADRs)

Architecture decisions are recorded as short documents in [`adr/`](../../adr/). Each records the context,
the decision, the consequences and the alternatives. Decisions are not edited when they change: a later
ADR supersedes an earlier one.

The current product is decided by [ADR-0018](../../adr/0018-regulatory-path-planner.md), which refocuses
the project on the regulatory path planner. [ADR-0017](../../adr/0017-first-product-refocus.md) records
the refocus itself.

| ADR | Title |
|---|---|
| [0001](../../adr/0001-fork-theopenlane-core-as-l1-substrate.md) | Use theopenlane/core as the substrate, vendored |
| [0002](../../adr/0002-orekit-jvm-microservice-for-l3.md) | Run Orekit as a JVM microservice |
| [0003](../../adr/0003-openmct-for-operator-dashboard-nextjs-for-portals.md) | openmct for the operator dashboard, Next.js for portals |
| [0004](../../adr/0004-lightrag-pattern-over-postgres-age-pgvector.md) | LightRAG pattern over Postgres, AGE and pgvector |
| [0005](../../adr/0005-trustgraph-context-cores-pattern-only.md) | TrustGraph context cores, pattern only |
| [0006](../../adr/0006-compliancenlp-architecture-for-l2-l4.md) | ComplianceNLP architecture for L2 to L4 |
| [0007](../../adr/0007-postgres-age-pgvector-as-production-kg-substrate.md) | Postgres, AGE and pgvector as the production knowledge graph |
| [0008](../../adr/0008-accord-nlp-rase-annotation-schema-for-corpus-labeling.md) | Annotation schema for corpus labelling |
| [0009](../../adr/0009-port-itu-compliance-monitor-snl-and-filing-maturity.md) | Port ITU compliance monitoring and filing maturity |
| [0010](../../adr/0010-mvp-llm-policy-claude-only.md) | MVP language-model policy: Claude only |
| [0011](../../adr/0011-external-security-review-quarkslab.md) | External security review: Quarkslab, with Cure53 as backup |
| [0012](../../adr/0012-fastapi-theopenlane-contract.md) | FastAPI and theopenlane contract |
| [0013](../../adr/0013-orekit-service-contract-rest-over-grpc.md) | Orekit service contract: REST over gRPC |
| [0014](../../adr/0014-claude-extractor-mvp-l2-l4-first-slice.md) | Claude extractor, first slice |
| [0015](../../adr/0015-openmct-first-slice-compliance-status-panel.md) | openmct first slice: compliance status panel |
| [0016](../../adr/0016-trust-bundle-first-slice.md) | Trust bundle, first slice |
| [0017](../../adr/0017-first-product-refocus.md) | First product refocus |
| [0018](../../adr/0018-regulatory-path-planner.md) | Regulatory path planner |

A review of the early engineering is in
[`adr/REVIEW-2026-05-15-eng-review.md`](../../adr/REVIEW-2026-05-15-eng-review.md).

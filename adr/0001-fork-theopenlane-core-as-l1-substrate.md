# ADR 0001 — Fork theopenlane/core as L1 substrate

**Status**: Accepted — 2026-05-15
**Decision-makers**: Maxime Kadr (solo)
**Supersedes**: v0.1 "build evidence vault from scratch" plan

## Context

ComplianceOS v0.1 plan called for building the L1 substrate (evidence vault + audit log + RBAC + SSO + controls + GraphQL API + questionnaire engine) from scratch in FastAPI. A solo build of this layer alone is ~6 engineer-months.

The deep resource assessment (see `docs/resource-assessment.md`) identified `theopenlane/core` as a near-complete Apache-2.0 implementation of exactly this layer: 2,037 commits, v1.20.6 release 3 days before this ADR, dogfooded by a commercial entity (theopenlane), with auto-generated audit history tables (Entgo), OpenFGA RBAC (Google Zanzibar-style), JWT/SSO/OIDC/Passkeys auth, GraphQL primary API, workflow engine, questionnaire engine, policy editors, and vulnerability ingestion connectors.

The catch: it is written in Go. ComplianceOS v0.1 chose FastAPI for the API surface.

## Decision

Adopt theopenlane/core as the **L1 substrate, vendored** (not GitHub-forked) at SHA `a76ccb5c35955ed8cb364a7aab65cec9808b854a` under `external/theopenlane-core/`.

Run theopenlane/core as a **dedicated Go service** behind its GraphQL API. FastAPI remains the Celestia-domain orchestration layer (space-specific business logic, drafting agent endpoints, frontend BFF). FastAPI calls theopenlane over GraphQL on the cluster-internal network.

Celestia extensions to theopenlane's data model live in `layers/L1-substrate/extensions/` as Openlane Framework definitions (YAML/JSON per Openlane's schema), NOT as patches to upstream Go files.

## Consequences

**Positive**
- L1 build collapses from ~6 months to ~3–4 weeks (model space frameworks as Openlane Frameworks, configure SSO/OpenFGA roles for operator/insurer/regulator).
- Apache-2.0 is clean for closed-source SaaS distribution.
- Inherit theopenlane's release cadence and security review surface (project has frequent releases).
- OpenFGA gives Celestia multi-tenant authorization "for free" — a substantial defensibility asset.

**Negative**
- Two-language backend (Go service + FastAPI). Solo build must learn enough Go to navigate, but not enough to extend upstream (work via Frameworks, not source edits).
- Strategic dependency on a single commercial entity (theopenlane) for upstream direction. Mitigated by Apache-2.0 license and vendored SHA pin.
- theopenlane sells the hosted version — must verify OSS feature parity stays intact. Track in `docs/upstream-watch.md`.
- Schema commitment: space obligations must be modeled as Openlane Frameworks/Controls. Lock-in risk if upstream schema changes incompatibly.

**EU sovereignty check**
- theopenlane/core is self-hostable. We deploy on Hetzner (DE). Upstream company is US-based but does not need to host our data. ✓ compatible with v0.1 sovereignty rules.

## Alternatives considered

- **Comp AI (AGPL-3.0)** — rejected; AGPL contaminates closed-source SaaS distribution.
- **Eramba / OpenGRC / GovReady** — older codebases, weaker workflow engines, no OpenFGA.
- **Build from scratch (v0.1 plan)** — adds 6 months; OpenFGA + audit history alone would take 2+ months solo to build correctly.

## Open questions

- OpenFGA model for the operator/insurer/regulator/admin role tetrad — see Phase 1 deliverables.
- Migration path if Celestia outgrows theopenlane's Framework schema — track in ADR-0010 (future).

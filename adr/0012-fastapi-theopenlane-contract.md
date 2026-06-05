# ADR 0012 — FastAPI ↔ theopenlane GraphQL contract

**Status**: Accepted — 2026-06-05
**Decision-makers**: Maxime Kadr (solo)
**Related**: [ADR-0001](./0001-fork-theopenlane-core-as-l1-substrate.md) (theopenlane as L1 substrate), eng review [REVIEW-2026-05-15](./REVIEW-2026-05-15-eng-review.md) issue **I-1**

## Context

ADR-0001 runs theopenlane/core as a Go service behind its GraphQL API (port 17608) and keeps
FastAPI as the Celestia orchestration / BFF layer. The eng review (I-1) flagged that the
**contract between them is undefined**, with two concrete risks:

- BFF endpoints couple directly to theopenlane's GraphQL schema, which drifts on every upstream SHA bump.
- Authorization responsibility is ambiguous — FastAPI BFF vs theopenlane's native OpenFGA — risking
  either double-enforcement gaps or sensitive-data leaks (an insurer/regulator reading evidence they
  shouldn't).

Three facts established while standing up Phase 1 shape this contract:

1. **theopenlane has no native framework-YAML import.** Frameworks/Controls/Evidence are created at
   runtime via GraphQL mutations (`createStandard`, `createControl`, `createSubcontrol`, `createEvidence`).
   The `catalog` tasks are Stripe billing, not compliance.
2. **The OpenFGA model is embedded and auto-written** by core on startup (`authz.createnewmodel: true`)
   from `fga/model/model.fga`. Its `organization` type has roles `admin / member / owner` plus
   group-based `*_creator` relations — there is **no operator / insurer / regulator** type. Editing
   `model.fga` is an upstream Go-source patch, forbidden by ADR-0001.
3. theopenlane's GraphQL endpoint is the single integration surface; there is no stable REST surface
   for the entities we need.

## Decision

**1. GraphQL is the only integration boundary.** FastAPI talks to theopenlane exclusively over
GraphQL at `http://core:17608/query`. No direct DB access to theopenlane's `core` database, no
patching upstream Go. A single typed client (`app/app/clients/openlane.py`) is the only module that
issues theopenlane GraphQL — domain routers depend on it, never on raw GraphQL strings scattered
across the codebase. This localizes upstream-schema drift to one file.

**2. The BFF curates a narrow surface; it does not proxy GraphQL 1:1 to browsers.** theopenlane's
GraphQL is never exposed to the frontends. FastAPI exposes a curated REST surface
(`/organizations`, `/frameworks`, `/evidence`, …) and translates to theopenlane GraphQL internally.

**3. The BFF is the authorization enforcement point for everything the upstream model cannot express.**
Every domain request resolves `current_user` + `org_id`, then performs an OpenFGA `check()` at the
BFF boundary **before** forwarding to theopenlane. Forwarding uses the user's own token so
theopenlane's native org-level checks also apply (defense in depth). The cross-org insurer/regulator
scoping (which org's evidence an insurer may underwrite, which jurisdiction a regulator covers) lives
**only** in BFF policy, because the upstream model has no cross-org concept.

**4. The 4-role tetrad (operator / insurer / regulator / admin) is realized on top of the embedded
model via OpenFGA Groups + relationship tuples, not by editing `model.fga`.** `admin` maps to native
org `admin`/`owner`; `operator` to org `member` + an `operators` group wired to the existing
`*_creator: [group#member]` relations; `insurer` / `regulator` to org `member` + groups, with their
read-scoping enforced at the BFF (decision 3). The Celestia tetrad spec lives in `cross-cutting/auth/`.

**5. SSO is theopenlane built-in auth + Dex (local OIDC) for the MVP.** A self-hosted EU-jurisdiction
IdP (Authentik or Keycloak) is deferred to Phase 4 production hardening. This satisfies the Phase 1
DoD ("a regulator can log in") at lowest risk and keeps identity EU-sovereign in production.

## Consequences

**Positive**
- Upstream schema drift is contained to one client module + the framework loader.
- Authorization has a single named enforcement point (the BFF), auditable in Phase 4's external review.
- No upstream patches → vendored SHA stays clean; upgrades are config + client changes only.

**Negative**
- Cross-org authorization logic concentrates in `app/` Python rather than the FGA model. This is
  trust-critical code; it must be covered by the Phase 5 external security review even though it is not
  under `app/api/trust/**`. Flag it explicitly in the audit hand-off.
- theopenlane has **no first-class EvidenceType registry**; Celestia's `evidence-types.yaml`
  (retention, mandatory_metadata, file_formats) is carried as BFF-side validation + Evidence `tags`/`source`.
- Tetrad-via-groups is more indirection than native roles would be; documented in `cross-cutting/auth/`.

**EU sovereignty check**
- Dex and theopenlane run in-cluster on Hetzner (DE); the production IdP (Phase 4) is EU-self-hosted.
  No US identity provider. ✓ compatible with sovereignty rules.

## Alternatives considered

- **Fork `model.fga` to add operator/insurer/regulator types** — rejected; it is an upstream Go-source
  patch (violates ADR-0001) and forces a merge burden on every SHA bump.
- **Proxy theopenlane GraphQL 1:1 to the frontends** — rejected; couples browsers to upstream schema and
  removes the BFF authorization boundary.
- **Stand up Keycloak/Authentik in Phase 1** — deferred to Phase 4; heavier setup with no MVP-DoD benefit.

## Open questions

- Exact `ghcr.io/theopenlane/core` image tag/digest matching vendored SHA `a76ccb5c` — pinned to
  `v1.20.6` for now (ADR-0001 cites that release); verify against GHCR and record in `docs/upstream-watch.md`.
- Whether a small Celestia-side EvidenceType metadata table is warranted once L2/L4 need richer
  evidence typing (revisit in Phase 3).

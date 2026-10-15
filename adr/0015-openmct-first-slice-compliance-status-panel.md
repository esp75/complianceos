# ADR 0015 — Phase 4 openmct first slice: Compliance Status panel over a BFF rollup endpoint

**Status**: Accepted — 2026-06-06
**Decision-makers**: Maxime Kadr (solo)
**Related**: [ADR-0003](./0003-openmct-for-operator-dashboard-nextjs-for-portals.md) (two frontends, one auth layer), [ADR-0012](./0012-fastapi-theopenlane-contract.md) (FastAPI↔theopenlane contract + BFF-boundary authorization), [ADR-0014](./0014-claude-extractor-mvp-l2-l4-first-slice.md) (first-slice discipline this follows)

## Context

Phase 4 (ROADMAP weeks 13–16) is the L5 dashboard phase: an openmct operator dashboard,
a Next.js insurer/regulator portal, the Ed25519/Merkle/PAdES trust layer, and Hetzner
deployment. That is far too much for one vertical slice. Phases 1–3 each landed a thin
end-to-end slice first (ADR-0014), proved offline and headless, with the heavy pieces behind
interfaces. Phase 4 gets the same treatment.

The natural first thread is the **operator's Compliance Status panel** — the L5 README's first
deliverable and the most direct consumer of work already built (L1 controls + org evidence). It
needs one piece of backend that does not exist yet: the existing API exposes frameworks/controls
(`GET /frameworks`) and an org's evidence (`GET /evidence?org_id=`) **separately**, with no
per-Framework/per-Control rollup. A panel that joins them on the client would re-implement a
tenancy- and authorization-sensitive join in Vue. That join belongs at the BFF.

## Decision

**1. The first slice is the openmct host scaffold + the Compliance Status panel only.** The
Evidence-Submission widget, ITU Filing-Maturity tracker, Conjunction Alarm strip, the Next.js
portal, OpenFGA-at-the-boundary hardening, the trust layer, and Hetzner/Coolify deployment are all
**deferred to later Phase 4 slices**. This slice proves the openmct plugin-host plumbing plus one
real, data-backed compliance view.

**2. The panel reads a new BFF rollup endpoint, `GET /compliance/status?org_id=`.** The BFF owns
the join: it fetches the visible Standards + Controls and the org's Evidence (with control
linkage), and rolls them up into a per-Framework, per-Control status with an org-level summary.
This keeps the tenancy join server-side, behind the `can_view` check (ADR-0012, `assert_can`), and gives the
panel a single typed payload. The rollup classification lives in a pure, unit-testable module
(`app/app/l5/rollup.py`), mirroring the `risk-scoring` separation in L3.

**3. v0 status classification is evidence-presence, not assessment workflow.** A control is
`compliant` when the org has at least one linked Evidence record in an accepted state,
`partial` when linked evidence exists but none is accepted, and `not_assessed` when none is
linked. Richer status (per-subcontrol `evidence_required` coverage, assessment frequency, breach
consequence) is a later refinement — the data is in theopenlane `descriptionJSON` and the payload
shape leaves room for it.

**4. openmct is consumed from the vendored substrate; the slice is proven headless.** The host
under `layers/L5-dashboard/openmct-host/` and the plugin under
`layers/L5-dashboard/plugins/compliance-status/` reference openmct at the pinned SHA in
`external/openmct/` (ADR-0003). The slice's proof is **a successful bundler build + unit tests on
the pure transform/adapter logic**, not a running browser. Browser-driven visual QA
(`/design-review`, `/qa`) and a deployed host are deferred to the deployment slice — consistent
with the headless/offline discipline of ADR-0014.

**5. No new backend dependency, no second store, no LLM.** The rollup is a pure function over two
GraphQL reads through the existing `OpenlaneClient` (ADR-0012, the single L1 boundary). The plugin
is a Vue 3 / openmct extension built with `bun` (already used for the Next.js apps per CLAUDE.md).

## Consequences

**Positive**
- The first operator-facing view is data-backed end-to-end (L1 controls + evidence → BFF rollup →
  openmct panel) in one slice, fully offline and CI-safe.
- The tenancy/authorization join is server-side and reuses the established `assert_can` seam.
- The host scaffold unblocks the remaining three plugins, which become additive: each is a new
  plugin + (where needed) a new BFF read endpoint, no rework of the host.

**Negative**
- v0 status is coarse (evidence-presence). It demonstrates the panel and the join, not a full
  assessment engine; the subcontrol-level `evidence_required` coverage is deferred.
- Two frontend toolchains remain in play (Vue for openmct, React for the portal) — unchanged from
  ADR-0003, just not exercised by the portal yet.

**EU sovereignty check**
- openmct is self-hosted JS, no runtime callback to NASA (ADR-0003). The rollup endpoint makes no
  external call beyond the in-cluster theopenlane substrate. Build artifacts are self-hosted. ✓

## Alternatives considered
- **Client-side join in the plugin** (call `/frameworks` + `/evidence` and merge in Vue) — rejected;
  pushes a tenancy- and authorization-sensitive join into the browser and duplicates logic the
  other plugins will also need server-side.
- **Start with the trust/bundle backend slice instead** — viable and valuable, but the operator
  needs something to *see*; the dashboard slice surfaces the L1–L4 work already done and the
  signed-bundle download is more naturally showcased once a view exists.
- **Full openmct production build of the vendored substrate now** — rejected for this slice; the
  substrate build belongs with the deployment slice. Here we prove the plugin bundle compiles.

## Open questions
- Auth token crossing from openmct (Vue) to the BFF — the slice uses a bearer token via the data
  adapter; the shared session-cookie scoping (ADR-0003 open question) is settled in the deployment
  slice.
- Whether subcontrol-level `evidence_required` coverage becomes its own status tier or stays inside
  the `partial` band — revisit once an operator uses the panel against real evidence.

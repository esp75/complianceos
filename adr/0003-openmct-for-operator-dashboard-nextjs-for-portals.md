# ADR 0003 — openmct for operator dashboard, Next.js for insurer/regulator portals

**Status**: Accepted — 2026-05-15
**Decision-makers**: Maxime Kadr (solo)

## Context

L5 (dashboard) serves three stakeholder groups with very different UI expectations:

- **Operators** are space engineers. They expect mission-control idioms: telemetry panels, time conductors, plan timelines, alarm strips. A generic SaaS dashboard feels alien.
- **Insurers** are risk underwriters. They expect portfolio-style dashboards, drill-down on per-asset risk, exportable reports, and side-by-side comparisons.
- **Regulators** are compliance reviewers. They expect document-centric views, audit-trail navigation, and evidence-bundle download flows.

v0.1's plan was a single Next.js 14 app for all three. This optimizes for engineering consistency but loses operator credibility.

**NASA Ames openmct** (Apache-2.0, 13k+ stars, 8,100+ commits, NASA-Ames maintained) is the de facto open-source mission-control framework. It is Vue 3. Plugin-first architecture — core is itself written as plugins. Operators recognize the idiom on sight.

## Decision

Adopt a **two-frontend split**:

- **Operator dashboard**: openmct host at SHA `3aaa0f05e9cc294412ac0557aef5fb82737e7c7e`, with Celestia plugins under `layers/L5-dashboard/plugins/`. Vue 3.
- **Insurer + regulator portals**: a single Next.js 14 App Router app under (future) `apps/portal/`, sharing components via shadcn/ui.

Both frontends authenticate against the same OpenFGA layer (from ADR-0001) so that a user with the right roles can move between them, and all backend calls go through the FastAPI orchestration layer (which proxies to theopenlane/core's GraphQL).

## Consequences

**Positive**
- Operators get the mission-control idiom they expect, plus implicit credibility from NASA's brand.
- Insurers/regulators get the polished portal UX appropriate for their workflows.
- Plugin-first openmct means Celestia compliance views are first-class extensions, not hacks.

**Negative**
- Two frontend stacks (Vue 3 for openmct, Next.js for portals) doubles the frontend ops surface (build pipelines, dependency security scans, design-system replication).
- Design system must produce both Vue 3 components (for openmct plugins) and shadcn/ui React components (for Next.js). Mitigated by Tailwind tokens shared across both.
- openmct learning curve is real (large codebase, plugin model).

**EU sovereignty check**
- openmct is self-hosted JS, no runtime callback to NASA. Build artifacts ship in our Hetzner-hosted nginx. ✓ compatible.

## Alternatives considered

- **Single Next.js for all three audiences** — engineering simpler, operator credibility weaker. Rejected.
- **openmct for all three audiences** — Vue 3 + plugin model is the wrong shape for insurer/regulator portal UX. Rejected.
- **Two Next.js apps (operator-themed vs portal-themed)** — solves design-system unification but loses NASA-mission-control credibility. Rejected.

## Open questions

- Auth token format crossing between Vue (openmct) and Next.js — likely a shared session cookie scoped to the parent domain, with OpenFGA decisions cached server-side. Decide in Phase 4.
- Whether to retain Jeffallan's `vue-expert` skill alongside `nextjs-developer`. Defer to Phase 4 when openmct plugin work begins.

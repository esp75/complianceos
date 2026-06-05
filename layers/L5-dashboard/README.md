# L5 — Dashboards

Two frontends, one auth surface. See [ADR-0003](../../adr/0003-openmct-for-operator-dashboard-nextjs-for-portals.md).

## Role

- **Operator dashboard**: mission-control idiom for satellite operators. Compliance status, evidence submission, ITU filing-maturity tracker, conjunction alarms.
- **Insurer + regulator portal**: polished portal UX. Portfolio risk views (insurer), evidence/audit views (regulator), PAdES-signed PDF bundles (regulator handoff).

## Architecture summary

- **Operator dashboard** (`openmct-host/` + `plugins/`) — openmct (Vue 3) plugin host. Celestia compliance views ship as openmct plugins.
- **Insurer + regulator portal** (`apps/portal/` future) — Next.js 14 App Router, TypeScript strict, Tailwind, shadcn/ui.
- **Shared auth**: OpenFGA decisions cached server-side; both frontends present a shared session cookie.
- **Shared design system**: see [`DESIGN.md`](../../DESIGN.md). Tokens and SVG icons shared; component implementations exist in both Vue and React variants.

## Sub-folders

- `openmct-host/` — openmct (vendored) hosting Celestia plugins
- `plugins/` — Celestia-original openmct plugins (Vue 3)

## Phase 4 deliverables (see ROADMAP.md)

- [ ] openmct host running locally, serving the Celestia plugin bundle
- [ ] Compliance Status plugin: per-Framework, per-Control status with drill-down to L1 evidence
- [ ] Evidence Submission plugin: drag-drop evidence files, prepopulate metadata from filename/EXIF, push to L1
- [ ] ITU Filing-Maturity plugin: state-machine visualization, alert on degradations
- [ ] Conjunction Alarm strip: realtime updates from L3 conjunction events
- [ ] Next.js portal app scaffolded (`apps/portal/`) with insurer + regulator routes
- [ ] OpenFGA enforcement at FastAPI boundary used by both frontends

## Skills to invoke

- `nextjs-developer` — primary skill for Next.js portal
- `/design-review` — visual QA after first plugin lands
- `/qa` — end-to-end test once auth + plugins + portal wire up
- `frontend-design` — production-grade UI generation
- context7 MCP — fetch openmct plugin authoring docs on demand

## Upstream reference

- openmct: `external/openmct/` at SHA `3aaa0f05e9cc294412ac0557aef5fb82737e7c7e`

## Open questions

- Shared session cookie scoping: parent domain (`*.celestia.dynamics`) vs subdomain isolation. Default: parent domain with HttpOnly + Secure + SameSite=Lax.
- Whether to ship Jeffallan's `vue-expert` skill alongside `nextjs-developer` for openmct plugin work. Defer to Phase 4 kickoff.
- Insurer portal export format: CSV (table) + signed PDF (per-asset). Confirm with first insurer pilot.

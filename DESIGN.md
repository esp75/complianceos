# ComplianceOS v0.2 — Design System

## Identity

ComplianceOS is operated by Celestia Dynamics. The product communicates two things first:

1. **Defensibility**. Regulators and insurers trust the math. Designed surfaces never let "AI feel" undermine that — no glowing gradients, no playful microcopy in evidence views.
2. **Mission-ops literacy**. Operators are space engineers. The product respects their idioms (TLE, conjunction probability, ascending node, frequency assignment) and never dumbs them down.

## Audience-specific surfaces

| Audience | Surface | Primary frontend | Design idiom |
|---|---|---|---|
| Operator | Operator Dashboard | openmct (Vue 3) | Mission-control — time conductors, telemetry strips, plan timelines, alarm panels |
| Insurer | Insurer Portal | Next.js 14 (shadcn/ui) | Underwriter portfolio — tables, drill-downs, exportable reports, risk heatmaps |
| Regulator | Regulator Portal | Next.js 14 (shadcn/ui) | Audit-grade document UI — evidence trees, citation graphs, PAdES-signed PDF download |
| Admin (Celestia internal) | Admin console | Next.js 14 | Configuration + tenant + role management |

## Tokens (shared across both frontends)

```
Color
  --bg              #0B0E14   slate-950 — operator-mode background
  --bg-paper        #11151D   one-step lighter — surfaces, panels
  --bg-portal       #F8FAFC   slate-50 — insurer/regulator light-mode default
  --fg              #E5E7EB   slate-200 — operator text
  --fg-portal       #0F172A   slate-900 — portal text
  --accent          #4F46E5   indigo-600 — primary action
  --accent-warm     #F59E0B   amber-500 — caution (do not flash; never red unless alarm)
  --alarm           #EF4444   red-500 — conjunction or noncompliance alarms only
  --success         #10B981   emerald-500 — completed evidence
  --info            #06B6D4   cyan-500 — neutral status (filing in progress, etc.)

Type
  Inter (UI), JetBrains Mono (telemetry, code, IDs)
  Operator: 14px base, 12px telemetry monospace
  Portal: 16px base, 14px tables, 18px section headers

Spacing
  4 / 8 / 12 / 16 / 24 / 32 / 48 / 64 — Tailwind defaults; portal uses denser 4/8/12 grid for tables

Radius
  Operator: 2px (mission-control feel — no soft corners)
  Portal: 6px (professional but not playful)

Motion
  Operator: 80ms reactions; no decorative animation
  Portal: 150ms easings; no skeleton-loading shimmer
```

## Anti-patterns (will fail design review)

- Gradient text or backgrounds in compliance assertions
- Emoji in evidence views, audit logs, or signed PDFs
- "AI generated" copy tone ("Let me help you with...", "Here are some insights...")
- Skeleton shimmers in operator-critical views (operators read shimmer as "not connected")
- Floating animated CTAs
- Light-mode operator dashboard (mission-control rooms are dim)

## Reference surfaces

For operator dashboard reference, study openmct's NASA-shipped demos (`external/openmct/example/`). Replicate the time conductor + telemetry strip patterns 1:1 for compliance status feeds.

For portal reference, the design language is closer to Vercel's dashboard, Stripe's invoicing surface, and Linear's issue views — quiet, dense, monospace-friendly, no decoration.

## Component library

Two builds from one source-of-truth:

- **Vue 3 build** (`packages/design-vue/`, future) — consumed by openmct plugins.
- **React + shadcn/ui build** (`packages/design-react/`, future) — consumed by Next.js portal.

Both consume the same Tailwind config and the same SVG icon set. Tokens defined once in `packages/design-tokens/`.

## Future

A formal `/design-consultation` run with `frontend-design` skill loaded should expand this into a full DESIGN_SYSTEM.md once the first openmct plugin lands (Phase 4). Until then, ADRs and these tokens are the source of truth.

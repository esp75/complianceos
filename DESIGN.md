# ComplianceOS — Design

## Who it is for

The planner's main user is whoever owns licensing at a satellite operator: a founder, a regulatory
lead, a programme manager. Many work at small operators with no regulatory department. They know
their mission well and the law less well. The product has to make three things easy:

1. **What do I need, and why?** Every requirement says why it applies to this mission, in plain
   language, with the article of law one click away.
2. **What do I do next, and by when?** Dates are worked back from the launch date, and the next
   action is always visible.
3. **Can I trust this?** Sources, retrieval dates, and how certain each number is are always shown.

## Principles

- **Defensibility first.** No claim without a source. Citations are chips that open the quoted text,
  the official URL and the date it was checked. If something is uncertain, the UI says so.
- **Plain language, precise terms.** "Start preparing by 9 Jun 2027", not "T-minus". Use regulators'
  names for things (advance publication, coordination request, bringing into use), with a short
  explanation the first time.
- **One next step.** Every screen answers "what now?": the next-actions strip, the next action on
  each tracked application, and the first item in the recommended sequence.
- **Honest about gaps.** Countries without data are named in warnings. Durations are labelled
  statutory, published practice or estimate. Draft data is labelled as draft.
- **Quiet and dense.** A document tool, not a dashboard toy. Generous line height and small type for
  metadata. No decoration that carries no information.

## Surfaces

| Surface | Purpose |
|---|---|
| Home | Two ways in: plan a mission, or open the sample. Coverage of the data. |
| Mission wizard | Four steps: operator, spacecraft and orbit, spectrum and services, markets and launch. A live preview shows which licences each answer brings in. |
| Mission workspace | Summary strip, warnings, and four tabs: Roadmap (next actions, timeline, per-country lists), Tracker (board), Deadlines (by month, calendar export), Brief. |
| Licence drawer | Why it applies, timing with certainty, quoted legal basis, documents and fees, local presence, obligations, who to contact, outside help, a drafted first email. |
| Application drawer | Allowed status changes only, dates, reference and notes, conversation log with next steps, full history. |
| Directory | Authorities with the contact channels they publish, and firms in their own words. |
| Data & sources | Coverage, how the data is checked, licences, how to contribute. |

The openmct operator dashboard (ADR-0003/0015) is parked under ADR-0017. Its mission-control idiom
(dark, 2px radii, telemetry strips) remains documented in the ADRs for when it returns.

## Tokens

Defined once as CSS variables in `web/src/app/globals.css` (HSL triplets) and mapped in
`web/tailwind.config.ts`. Light is the default; dark follows the system or the header toggle.

| Token | Light | Dark | Use |
|---|---|---|---|
| `background` | warm paper `hsl(40 20% 98%)` | `#0B0E14` | page |
| `surface` | white | `#11151D` | cards, drawers |
| `foreground` | slate-900 | slate-200 | text |
| `muted-foreground` | slate-600 | slate-400 | metadata |
| `border` | warm grey | slate-800 | dividers |
| `accent` | indigo-600 | indigo-300 | primary actions, citations, critical path |
| `ok` | emerald | emerald | on track, granted |
| `warn` | amber | amber | tight slack, information requested, warnings |
| `alarm` | red | red | **late and overdue only** |
| `info` | sky | sky | submitted, under review |

- **Type:** Inter (variable) for UI; JetBrains Mono for citation ids, codes and counts. Base 15px.
  Both self-hosted through Fontsource, with no third-party font requests.
- **Radius:** 6px controls, 8–10px cards.
- **Status is never colour alone.** Every coloured state also has a word (On track, Tight, Late,
  Overdue, Granted…).
- **Certainty styling:** statutory durations get a solid outline badge, published practice a filled
  neutral badge, estimates a dashed badge.

## Interaction

- Drawers (right-hand sheets) for detail, so the roadmap stays in view. `Esc` closes.
- Destructive actions use a two-step inline confirm, never a browser dialog.
- Errors explain the fix ("Can't reach the planner API… start it with `docker compose up`") rather
  than showing a raw message.
- Motion is limited to colour transitions and is disabled under `prefers-reduced-motion`.

## Accessibility

Target WCAG 2.2 AA:
- semantic headings and landmarks, plus a skip link;
- visible focus rings;
- `aria-pressed`/`aria-checked` on toggle chips and choice cards;
- text alternatives on the timeline rows;
- contrast-checked tokens in both themes.

Every page is checked at 390px wide for horizontal overflow.

## Anti-patterns (fail review)

- Gradient text or backgrounds on anything that asserts compliance.
- Emoji in roadmaps, evidence views, audit logs or exported PDFs.
- "AI" tone in copy ("Let me help you…", "Here are some insights…"). The brief reads like a
  regulatory memo.
- A number or date without its basis: every duration shows statutory / practice / estimate.
- Red for anything other than late or overdue.
- Skeleton shimmer for data that failed to load. Say what failed and how to fix it.

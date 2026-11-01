# ADR 0022 — Dossier: friction points, decision makers, basis labels, reviewer package

**Status**: Accepted — 2026-11-01
**Decision-makers**: Maxime Kadr (solo)
**Related**: [ADR-0014](./0014-claude-extractor-mvp-l2-l4-first-slice.md) (citation-or-422),
[ADR-0018](./0018-regulatory-path-planner.md) (brief, dossier), [ADR-0021](./0021-signed-history-and-pilot-usage.md)

## Context

ROADMAP P1 asks for a dossier with an objection forecast and a decision-maker map, a practice-versus-
statute confidence label on each claim, and a reviewer loop with a diff-friendly format. The pack
holds rules, citations, authorities and contact channels. It holds no record of how any authority has
objected to past applications.

## Decision

1. **"Likely friction points" replaces "objection forecast".** The section lists where an application
   is likely to be delayed or questioned, using only what the pack records: prerequisite ordering,
   local-presence requirements, processing times with no official figure, thin schedule margin, and
   rule records that no practitioner has reviewed. It does not claim to know how a regulator has
   behaved. A real objection-pattern layer needs practice data collected and sourced per
   jurisdiction; that is P3 work and is not faked here.
2. **"Who decides" is the decision-maker map.** For each licence: the deciding authority and its
   roles, what comes before it, and the authority's published contact channels (from the pack, each
   with its own source). Named individuals are not recorded unless an authority publishes them.
3. **Every paragraph can carry a basis label:** `statute` (stated in the cited text), `practice` (an
   authority's published practice), `estimate` (no official figure; the planner's own) or `derived`
   (computed from dates and the rules above). Labels show in the PDF and the reviewer package.
4. **Both new sections are grounded.** The same enforcer that guards the summary rejects a paragraph
   without a `[cite:<id>]` that exists in the roadmap, so the brief cannot be built with an uncited
   claim.
5. **The reviewer package is Markdown** (`GET /missions/{id}/dossier.md`): fixed order, no
   timestamps beyond the roadmap date, citations quoted with source and retrieval date, a checklist
   per licence and a sign-off block. Two exports of the same data are byte-identical, so a rule change
   appears as a plain diff. It reports the count of grounded paragraphs without a citation (zero by
   construction) and of rule records still draft.

## Consequences

- The P1 definition of done ("zero uncited claims") is checked mechanically, but "passes expert
  review" still needs an expert: the checklist is for them.
- The friction section will say little for jurisdictions with few recorded constraints. That is a
  statement about the pack, not about the regulator.
- Still open in P1: corpus for the pilot jurisdictions (DE, AT), a real objection-pattern layer,
  and ingest of national acts through the L2 extractor.

## Addendum: the signature covers the brief

The first dossier signature covered the roadmap only, so the cited prose added here (friction
points, decision makers, basis labels) could change after signing. The signed bytes are now the
canonical JSON of `{format, roadmap, brief}` (`complianceos-dossier/1`). The existing workspace
Ed25519 key signs it through the same trust primitives; no trust-layer file changed, and
`POST /bundle/sign` (which seals an organisation's Openlane evidence) is not involved. The key is
embedded, so a verifier must compare the fingerprint with one obtained separately.

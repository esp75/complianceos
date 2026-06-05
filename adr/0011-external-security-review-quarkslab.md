# ADR 0011 — External security review vendor: Quarkslab (primary), Cure53 (backup)

**Status**: Accepted — 2026-05-15
**Decision-makers**: Maxime Kadr (solo)
**Resolves**: STATUS.md open question #5

## Context

Per v0.1's CLAUDE.md, trust-layer code (`app/api/trust/**`, `app/api/rls/**`, `app/api/bundle/sign*.py`, plus L4 provenance) is reserved for paid external security review. Budget: €12k–€18k. Phase 5 (post-MVP, weeks 17–20).

Three vendors were on the v0.1 shortlist:

- **Trail of Bits** (US) — top-tier reputation, deep expertise in cryptographic primitives + Merkle trees. Drawback: US jurisdiction conflicts with EU sovereignty narrative (regulators will ask).
- **Quarkslab** (France) — French security firm with strong track record in cryptographic protocol review, embedded crypto, audit-grade software reviews. Has reviewed Ed25519 implementations, signing infrastructure, and compliance-adjacent code. EU jurisdiction.
- **Cure53** (Germany) — German firm widely respected for browser/crypto/web-stack reviews. EU jurisdiction. Strong track record on signed-document and PDF-handling reviews.

## Decision

**Quarkslab is the primary external review vendor. Cure53 is the named backup.**

### Why Quarkslab

1. **French jurisdiction** — best match for an EU-sovereign French-origin compliance product. When a French/EU regulator asks "who audited your trust layer?", "Quarkslab" lands harder than "Trail of Bits" or "Cure53" in that audience.
2. **Cryptographic protocol expertise** — Ed25519 + Merkle audit chain + PAdES PDF signing is exactly the protocol-review wheelhouse Quarkslab is known for.
3. **Compliance-adjacent track record** — Quarkslab has reviewed software for ANSSI-graded environments and is recognized in EU regulatory circles.
4. **Bilingual reporting (EN/FR)** — useful when the same report needs to be handed to a French insurer and an English-speaking certification body.

### Why Cure53 as backup

1. EU jurisdiction (Germany) — preserves sovereignty narrative if Quarkslab is unavailable.
2. Public engagement reports demonstrate ability to handle audit-grade reviews.
3. Strong PDF/signing review track record relevant to the PAdES bundle code.

### Why not Trail of Bits

- US jurisdiction. Even though their technical work is excellent, a regulator-defensibility report from a US firm undermines the EU-sovereignty pitch we are selling to insurers and regulators. The cost of inconsistency is higher than the cost of slightly less-famous EU alternatives.

## Consequences

**Positive**
- Single coherent EU-sovereignty narrative end to end: EU infrastructure + EU audit + EU LLM endpoint.
- Quarkslab's cryptographic expertise aligns with the actual trust-layer attack surface.
- Backup vendor identified → contingency if scheduling slips.

**Negative**
- Quarkslab's lead times are non-trivial (typically 4–8 weeks ahead). Need to book by end of Phase 3 to hit Phase 5.
- Quarkslab quotes may be higher than Cure53 for equivalent scope. Need to scope-down to fit €12k–€18k budget. Mitigation: pre-scope the review tightly — only the marked-for-external-review surface, plus the Merkle chain integrity proofs.

## Action items (carry into Phase 3 / Phase 5 prep)

1. Phase 3 week 1: Send Quarkslab a preliminary RFP with the marked-for-external-review file list, line-counts, and architecture summary (this repo's `ARCHITECTURE.md` + `CLAUDE.md` is sufficient).
2. Phase 3 week 8: Confirm Quarkslab availability for Phase 5 window. If declined or unavailable, escalate to Cure53.
3. Phase 4: Freeze trust-layer code for review. Tag a `pre-audit-v0` git tag for the review baseline.
4. Phase 5: Execute review. Track findings against an audit-tracker (file under `docs/audit-findings.md`, with severity + status + remediation PR link).

## Alternatives considered

- **Trail of Bits primary, Cure53 backup** — rejected on jurisdiction grounds. Reconsider only if EU-sovereignty narrative drops in priority.
- **Cure53 primary, Quarkslab backup** — Cure53 is excellent but Quarkslab's cryptographic-protocol track record is closer to the v0.2 trust-layer attack surface (Ed25519 + Merkle + PAdES).
- **Skip external review for MVP, defer to v2** — rejected; insurers and regulators will demand it before any production data lands.

## Open questions

- Exact RFP wording — defer to Phase 3 prep.
- Whether to also engage ANSSI's CSPN qualification for the trust layer post-Quarkslab review. Tracker question; defer to v1.1.

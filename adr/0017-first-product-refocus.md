# ADR-0017 — First-product refocus: AI regulatory-affairs for satellite operators (market access)

**Status:** Accepted (2026-07-23)
**Supersedes (as first-product definition):** the EU-Space-Act-obligation wedge implicit in ADR-0001–0016 scoping; those ADRs remain accepted for the layers that carry over.
**Context docs:** the full strategy analysis lives intentionally outside the repo (audit-surface rule, CLAUDE.md).

## Context

Field evidence (operator-side advisory discovery, July 2026) established that present-tense, enforcement-backed spend in space compliance sits in **licensing / market access**, not in pre-2030 EU Space Act obligation tracking: every operator must be licensed per jurisdiction to operate and to enter each new market; advisory incumbents price the entry artifact (per-country regulatory roadmap) at $5–10k and structurally exclude small operators; no product serves that long tail. The EU Space Act applies from 2030 and becomes a *second obligation stream* into the same platform, not the first product.

## Decision

Celestia's first product is an **AI regulatory-affairs capability for satellite operators** (working identity: "the AI regulatory-affairs firm"), transacted as a ladder:

1. **Market-Access Dossier** (per jurisdiction): citation-grounded requirements map, sequencing/timeline, prerequisites, objection forecast, decision-maker map — produced by the L2/L4 pipeline, human-reviewed, delivered inside a live workspace.
2. **The Watch** (subscription, per jurisdiction): continuous monitoring of regulatory sources, deltas mapped to the client's applications, refreshed briefs, program tracker.
3. **Program of record** (grows organically): multi-market state, signed history via the trust layer.

Go-to-market opens with a 3-slot founding pilot (free deliverable against LOI + MoU with pre-agreed conversion terms). Commercial detail stays outside the repo.

**Sovereignty framing:** sovereign **by design**, sold globally. EU infrastructure remains the implementation (CLAUDE.md rules unchanged); "your licensing state lives where you control it" is a global sales property, not an EU market boundary.

## Consequences — what carries, what parks

| Layer / asset | Verdict | Notes |
|---|---|---|
| L1 substrate (theopenlane, OpenFGA tetrad, BFF) | **Carries** | Roles re-map toward operator/advisor/admin; regulator/insurer roles dormant |
| L2 KG (PG17+AGE+pgvector, ingest, Claude extractor) | **Carries, re-targeted** | Ingest target becomes national telecom/space acts + ministry sources per pilot jurisdiction (was framework YAMLs) |
| L4 retrieval + drafting + citation enforcer | **Carries** | Becomes the dossier/brief engine; citation-or-422 is the product's accuracy story |
| Trust layer (Ed25519/Merkle/signed bundles, ADR-0016) | **Carries, reframed** | "Signed program history"; MARKED-FOR-EXTERNAL-REVIEW + Quarkslab plan (ADR-0011) unchanged |
| L3 SDER engine (Orekit service, ITU port, risk scoring; ADR-0002/0009/0013) | **Parked** | No role in the first product; container shelved, code retained; revisit with EU Space Act stream (2028+) |
| L5 openmct host + compliance panel (ADR-0015) | **Parked** | Mission-control idiom does not serve a licensing buyer; client workspace will be a lightweight web UI (Next.js path per ADR-0003 remains the portal framework) |
| EU Space Act / ISO 24113 / ITU framework YAMLs | **Retained** | Dormant first-party content; ITU RR corpus partially reusable for spectrum-licensing dossiers |
| LEGAL-BERT/Doccano, PAdES-B-LT, EU IdP | Deferred (unchanged) | Per ADR-0014/0016 deferrals |

## Alternatives considered

(a) Stay the course (EU Space Act wedge) — rejected: no pre-enforcement spend, lane contested, 2030 timeline. (b) Licensing program-of-record SaaS as the wedge — rejected as *entry* (system-of-record adoption cannot be a first transaction from an unknown vendor) but retained as the ladder's third act. (c) Pure consulting — rejected: nothing compounds. Analysis and scoring in the external strategy doc.

## Revisit triggers

EU Space Act trilogue conclusion materially accelerating obligations; pilot gate failure (per external doc §10 tripwires); any funded direct competitor entering long-tail market access.

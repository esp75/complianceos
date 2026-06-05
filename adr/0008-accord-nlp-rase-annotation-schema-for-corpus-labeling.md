# ADR 0008 — accord-nlp RASE annotation schema for L2 corpus labeling

**Status**: Accepted — 2026-05-15
**Decision-makers**: Maxime Kadr (solo)

## Context

Building the SpaceRegObligation corpus (the labeled training set for ADR-0006's multi-task LEGAL-BERT) requires an annotation schema. **Accord-Project/accord-nlp** (Apache-2.0, Horizon Europe ACCORD project) developed a two-stage NER+RE pipeline for building-code regulatory text with `<e1>`/`<e2>` markup tokens, the **CODE-ACCORD corpus** (6,375 relations), and the **RASE** annotation scheme (Requirement, Applicability, Selection, Exception).

RASE is generic enough to apply across regulatory domains and has been used in the EU AEC compliance research community.

## Context

Adopt RASE as the **annotation scheme** for the SpaceRegObligation corpus.

- Vendor accord-nlp at SHA `f1bc23101b5eec36926732728f05ba1e3001de15` for reference.
- Schema lives at `layers/L2-knowledge-graph/ontology/RASE-celestia.md` (future) — extends RASE with space-specific entity types (Orbital Slot, Satellite Class, Frequency Band, etc. — same as ADR-0006).
- Annotation tool: default to **Doccano** (EU-hostable, MIT) for labeler UX.
- Inter-annotator agreement target: ≥0.85 Cohen's kappa before training begins.

## Consequences

**Positive**
- RASE is well-understood in EU regulatory-NLP research; adopting it gives Celestia a citable methodology.
- Compatible with ComplianceNLP's three-head architecture (ADR-0006) — RASE supplies the labels.
- Annotation effort is bounded and measurable.

**Negative**
- RASE was designed for building codes; space-specific elements require schema extension and validation.
- Annotation is labor-intensive; budget a contracted labeling effort or solo-build a small seed corpus first.

**EU sovereignty check**
- accord-nlp is EU-funded (Horizon Europe). RASE has EU research provenance. ✓ aligns with EU sovereignty narrative.

## Alternatives considered

- **BIO/BIOES tagging only** — works for NER but not for the RASE-style applicability/selection/exception logic needed for compliance reasoning. Rejected.
- **Custom Celestia annotation schema** — reinvents the wheel and forfeits prior-art defensibility. Rejected.
- **Direct LLM extraction without annotation** — non-deterministic, fails reproducibility bar. Rejected (use only for bootstrapping draft labels for human review).

## Open questions

- Doccano vs Prodigy vs Label Studio for the annotation UI. Default Doccano (free, EU-hostable); revisit if throughput matters.
- Whether to release the corpus and schema publicly post-Phase 3 to drive ecosystem adoption.

# EU Space Act — Framework Definition

Celestia's machine-actionable representation of the EU Space Act (Regulation proposed 2025, current text reference: COM(2025) — placeholder until final OJ publication; update once Official Journal version is released).

## What lives here

- `framework.yaml` — the top-level Openlane Framework manifest
- `articles/article-01.yaml` — Article 1: Subject matter and scope
- `articles/article-02.yaml` — Article 2: Definitions
- `articles/article-03.yaml` — Article 3: Authorisation regime
- `articles/article-04.yaml` — Article 4: Competent authorities
- `articles/article-05.yaml` — Article 5: Insurance and financial guarantees
- `evidence-types.yaml` — Celestia-defined evidence types this Framework references

## Authoritative source

Until the EU Space Act is finalized and published in the Official Journal:

- Source document: European Commission proposal COM(2025) — full text and supporting Impact Assessment
- Citation pattern in this Framework: `EU-SA Art.<N>(<sub>)` (e.g., `EU-SA Art.3(1)`)
- Update protocol: when the OJ-final text differs from the proposal, write an ADR and re-version this Framework.

## RASE annotation

Every Control in this Framework carries RASE slots (see [ADR-0008](../../../../adr/0008-accord-nlp-rase-annotation-schema-for-corpus-labeling.md)):

- **Requirement** — what must / shall be true (deontic modality from L2 extractor)
- **Applicability** — to which entities (operator types, satellite classes, frequency bands)
- **Selection** — under which conditions (e.g., LEO vs GEO; mass thresholds; mission phase)
- **Exception** — explicit carve-outs

These slots feed directly into L2 KG ingestion and L4 retrieval; do not omit them.

## Phase 1 status

Articles 1–5 below scaffold the Framework with the **proposal-version** text and conservative interpretations. Marked `validation_status: draft` until reviewed against the OJ-final text in Phase 1 week 3.

```
Articles included in this scaffold:
  ✓ Article 1 — Subject matter and scope
  ✓ Article 2 — Definitions
  ✓ Article 3 — Authorisation regime
  ✓ Article 4 — Competent authorities
  ✓ Article 5 — Insurance and financial guarantees

Articles deferred to later in Phase 1:
  Article 6+ (cybersecurity, sustainability, registration, debris mitigation, transitional)
```

## Validation checklist (Phase 1 week 4)

- [ ] Hand-validate each Control against the EU Space Act Articles 1–5 (proposal version + OJ-final if available)
- [ ] Cross-check overlapping ISO 24113 obligations and add `cross_references` edges in L2
- [ ] Confirm `applicability` rules match EU member-state interpretations (consult the Annex-listed Member State authorities once defined)
- [ ] Confirm `evidence_types` are loadable by theopenlane and emit correctly in audit logs
- [ ] Flip `validation_status` from `draft` to `accepted`

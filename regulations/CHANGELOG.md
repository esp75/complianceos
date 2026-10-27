# Reg-graph changelog

Every change to the regulation files in this directory must be logged here with date, source, and rationale. The reg-graph is Celestia's unique leverage — its history must be auditable.

## 2026-10-27 — Phase 1 schema v2

- Schema moved to pydantic models in `app/api/reggraph/models.py`; `schema.yaml` is now the documented view (version 2).
- Added `Citation` object (kind, celex, document_id, url, article, paragraph, point, consolidated_date, verified_at, verified_by).
- Added `review_status` (draft | author_reviewed | lawyer_reviewed), `valid_to`, `applies_when`, `evidence_required`, `retention_years`, `response_window`, `authority`.
- Edge types now mirror AGE labels; added `supersedes` and `references`.
- Rationale codes added: `AUTHORISATION_SUPERVISION`, `COLLISION_AVOIDANCE_SERVICES`. Insurance stays under `THIRD_PARTY_LIABILITY` rather than a new code, to avoid two codes for one obligation family.
- Source: Phase 1 plan (`~/.claude/plans/start-1-ph1-reg-graph-velvet-stonebraker.md`). No lawyer review is recorded for any entry; the corpus is "citation-verified, author-reviewed" at most.

## 2026-05-15 — Phase 0 scaffold

- Initialised `schema.yaml` with obligation record format.
- Created empty obligation files for: EU Space Act, FCC 22/74, ITU filings, ISO 24113.
- Defined initial `rationale_codes.yaml` vocabulary.

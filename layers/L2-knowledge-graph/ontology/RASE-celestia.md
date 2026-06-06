# RASE-celestia — L2 ontology (v0)

The schema for the L2 knowledge graph in the Postgres + AGE + pgvector substrate (ADR-0007).
RASE (Requirement / Applicability / Selection / Exception, ADR-0008) supplies the per-obligation
slots; the entity and edge catalogs below extend it for the space-regulatory domain.

> v0 scope (ADR-0014): obligations are materialized deterministically from the loaded framework
> YAMLs; the Claude/LEGAL-BERT extractor populates these same shapes from unstructured text. This
> doc defines the **shapes**, not the full 23+ entity-type catalog of ADR-0006 (that lands with the
> trained extractor).

## Graph: `celestia_kg` (AGE)

### Node labels

- **Obligation** — the core node. One per framework control/citation. Properties:
  - `ref_code` (unique, e.g. `"ISO 24113 §6.2"`) — matches the L1 Control `refCode`
  - `framework` (e.g. `"iso-24113"`)
  - `title`
  - `deontic` — one of `SHALL` / `MUST` / `SHOULD` / `MAY` / `MUST_NOT`
  - `requirement`, `applicability`, `selection`, `exception` — RASE slots (text)
  - `evidence_types` — list of L1 evidence-type names this obligation requires

- **EvidenceType** — an L1 evidence-type vocabulary term (e.g. `disposal-telemetry`). Properties:
  `name`, `framework`.

### Edge types (v0 subset of the ARCHITECTURE.md catalog)

- `(Obligation)-[:CITES]->(Obligation)` — a regulatory cross-reference between obligations.
- `(Obligation)-[:REQUIRES_EVIDENCE]->(EvidenceType)` — the evidentiary requirement.

Future (deferred): `applies_to`, `superseded_by`, `derived_from` (provision-level), `has_filing_state`.

## Relational tables (pgvector + provenance)

- **`obligation_embedding`** — vector index for retrieval (LightRAG local level, ADR-0004):
  `ref_code TEXT PRIMARY KEY`, `framework TEXT`, `content TEXT`, `embedding vector(384)`.
  Dim 384 is forward-compatible with `BAAI/bge-small`/`bge-m3` (the production embedding swap).

- **`context_core`** — provenance per cited source (Context Cores, ADR-0005). One row per source a
  draft cites, so "every claim has a Context Core":
  `id`, `draft_id`, `source_type` (`obligation`|`evidence`), `source_ref`, `derivation`,
  `created_at`.

## Mapping from the L1 framework YAML

Each `kind: Control` YAML (e.g. `layers/L1-substrate/frameworks/iso-24113/articles/clause-6-2.yaml`)
maps to one Obligation:

| YAML | Obligation property |
|---|---|
| `metadata.citation` | `ref_code` |
| `metadata.framework` | `framework` |
| `metadata.display_name` | `title` |
| `spec.deontic_modality` | `deontic` |
| `spec.rase.{requirement,applicability,selection,exception}` | RASE slots |
| `spec.controls[].evidence_required[]` (union) | `evidence_types` → `REQUIRES_EVIDENCE` edges |
| cross-refs in `spec` (e.g. "EU-SA Art.4") | `CITES` edges |

Embedded content for retrieval = `title + requirement + applicability` (the parts a compliance
question matches against).

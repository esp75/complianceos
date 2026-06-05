# L2 — Knowledge Graph

Regulation-as-code substrate over Postgres 17 + Apache AGE + pgvector. See ADRs [0006](../../adr/0006-compliancenlp-architecture-for-l2-l4.md), [0007](../../adr/0007-postgres-age-pgvector-as-production-kg-substrate.md), [0008](../../adr/0008-accord-nlp-rase-annotation-schema-for-corpus-labeling.md).

## Role

Turn regulatory text into machine-actionable obligations with explicit cross-references, applicability rules, and evidentiary requirements. Source of truth for what every Framework Control means.

## Architecture summary

- **Storage**: Postgres 17 with Apache AGE (graph) and pgvector (vector) extensions. Single multi-tenant DB with RLS by Organization.
- **Extractor pipeline**: LEGAL-BERT encoder + three joint heads (NER, deontic modality, cross-reference). Per ComplianceNLP architecture (Guo et al., arXiv:2604.23585).
- **Annotation schema**: RASE (Requirement, Applicability, Selection, Exception) from accord-nlp, extended with space-specific entity types.
- **Ingest flow**: regulation PDF → parser → extractor → AGE graph + pgvector chunks → human-in-loop review queue → published obligations.

## Sub-folders

- `ontology/` — RASE-celestia schema + entity-type catalog + edge-type catalog
- `extractors/` — LEGAL-BERT pipeline (NER + modality + cross-ref); shared with L4
- `corpus/` — SpaceRegObligation: annotated provisions for training and evaluation
- `ingest/` — pipelines that push parsed/extracted obligations into AGE + pgvector

## Phase 3 deliverables (see ROADMAP.md)

- [ ] Doccano annotation environment deployed on Hetzner
- [ ] RASE-celestia schema document
- [ ] 200–500 annotated provisions across EU Space Act + ISO 24113 (corpus seed)
- [ ] LEGAL-BERT LoRA adapters: NER, modality, cross-ref
- [ ] Ingest pipeline: PDF → parser → extractor → AGE + pgvector
- [ ] Held-out evaluation: F1 ≥ 0.75 on each head before production use; human-in-loop until 0.85

## Skills to invoke

- `rag-architect` — for retrieval-shaped extractor decisions
- `prompt-engineer` — for any LLM-assisted bootstrap labeling
- `postgres-pro` — for AGE schema + index strategy
- `database-optimizer` — for KG query tuning

## Upstream reference

- Architecture: `external/compliance-nlp/` at SHA `8a85f38aef6720eeeb7e25ba97b91f5e55f3ca3b`
- Annotation: `external/accord-nlp/` at SHA `f1bc23101b5eec36926732728f05ba1e3001de15`
- Models: LEGAL-BERT base (nlpaueb/legal-bert-base-uncased) — mirror weights to EU storage before Phase 3

## Open questions

- Adapter strategy: LoRA vs full fine-tune vs prompt-tune. Default LoRA; benchmark.
- Bootstrap labeling: GPT-4-class for draft labels reviewed by human, or human-only from start. Default: GPT-4 draft, human review (with sovereignty caveat documented).

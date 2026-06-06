# ADR 0014 — Claude-as-extractor for the L2/L4 MVP first slice (LEGAL-BERT deferred)

**Status**: Accepted — 2026-06-06
**Decision-makers**: Maxime Kadr (solo)
**Related**: [ADR-0006](./0006-compliancenlp-architecture-for-l2-l4.md) (ComplianceNLP/LEGAL-BERT target — this defers it), [ADR-0004](./0004-lightrag-pattern-over-postgres-age-pgvector.md) (LightRAG retrieval pattern), [ADR-0005](./0005-trustgraph-context-cores-pattern-only.md) (Context Cores), [ADR-0007](./0007-postgres-age-pgvector-as-production-kg-substrate.md) (PG+AGE+pgvector), [ADR-0008](./0008-accord-nlp-rase-annotation-schema-for-corpus-labeling.md) (RASE), [ADR-0010](./0010-mvp-llm-policy-claude-only.md) (Claude-only MVP LLM)

## Context

Phase 3 builds L2 (regulation-as-code KG) and L4 (citation-grounded drafting). The full
ADR-0006 path — deploy Doccano, hand-annotate a 200–500 provision SpaceRegObligation corpus,
train LEGAL-BERT LoRA heads (NER / deontic / cross-ref) to F1 ≥ 0.75 — is a multi-week ML
project needing annotation labour, GPU, and EU weight mirroring. That does not fit a first
vertical slice, and it does not on its own reach the Phase-3 DoD (a cited compliance
paragraph). We need the DoD thread working first, with the heavy ML deferred.

Two facts make a lighter slice possible:
1. **The loaded frameworks are already structured obligations.** Phase 1 hand-authored ISO
   24113 / ITU / EU Space Act as YAML controls carrying RASE slots, deontic modality,
   `evidence_required`, and cross-refs. L2 can materialize these into the KG **without any
   model** — the extractor is only needed for *unstructured* regulation text.
2. **The MVP LLM is Claude (Anthropic EU, ADR-0010).** Claude can do the NER/deontic/RASE
   extraction from raw text directly, good enough for a v0 ingest, while LEGAL-BERT remains
   the production target.

## Decision

**1. v0 L2 population is deterministic from the loaded frameworks.** The L2 ingest parses the
Phase-1 framework YAMLs into `Obligation` nodes in the AGE graph `celestia_kg` plus per-obligation
embeddings in pgvector, with `CITES` (cross-ref) and `REQUIRES_EVIDENCE` edges. No model, no LLM,
fully offline and reproducible. This is what populates the KG for the DoD demo.

**2. The extractor is Claude-as-extractor for unstructured text (LEGAL-BERT deferred).** For raw
regulation text (no YAML), the L2 extractor calls Claude (Anthropic EU) to produce typed RASE
obligations. This honours the ADR-0006 *architecture intent* (NER + deontic + cross-ref + RASE)
with a different engine for the MVP. The **LEGAL-BERT three-head pipeline, Doccano corpus, and
LoRA training of ADR-0006/0008 are deferred to a post-MVP phase.** The extractor sits behind an
interface so the LEGAL-BERT engine swaps in without touching callers.

**3. v0 embeddings are a deterministic hashing embedding; bge-m3 is the production swap.** To keep
the slice offline and sovereign-by-construction (nothing leaves the box, no HF download), v0 uses a
dependency-free hashing embedding at **dim 384** (forward-compatible with `BAAI/bge-small`/`bge-m3`).
Retrieval quality is lexical-overlap, sufficient to surface ≥2 related obligations for the DoD.
`EmbeddingProvider` is an interface; the real bge-m3 model (ADR-0004, EU-hosted) slots in later.

**4. v0 retrieval is the LightRAG dual-level pattern minus the reranker.** pgvector ANN (local) +
AGE Cypher traversal (global) + simple score fusion. `BAAI/bge-reranker-v2-m3` (ADR-0004) is
deferred — it needs GPU/EU inference hosting and is a quality refinement, not a DoD blocker.

**5. The drafting agent runs behind a provider-router LLM interface; offline it uses a
deterministic cited-paragraph provider.** `app/app/llm/` holds the `LLMProvider` interface and an
`AnthropicEUClient` (ADR-0010). When no Anthropic EU key is configured, a deterministic provider
templates a compliance paragraph from the retrieved obligations + evidence, so the slice runs and
the DoD is demonstrable with **no key and no US LLM call**. A live key is a config swap.

**6. v0 drafting code is NOT yet under `app/api/trust/`.** The L4 README reserves
`app/api/trust/draft/**` for the signed-PDF path. v0 produces a cited paragraph + structured JSON,
not a PAdES bundle, so it lives in `app/app/api/draft.py` (un-marked) for now. It **migrates to
`app/api/trust/draft/` and gains the `# MARKED-FOR-EXTERNAL-REVIEW` header when PAdES signing +
final provenance land** (Phase 4/5, before the Quarkslab review). Recorded here so the move isn't
forgotten.

## Consequences

**Positive**
- The Phase-3 DoD (cited compliance paragraph with Context Cores) is reachable in one slice,
  fully offline and CI-safe, with no annotation labour, GPU, or live LLM key.
- Every deferred piece (LEGAL-BERT, bge-m3, reranker, live Claude, PAdES/trust-marking) sits
  behind an interface, so swapping it in is additive, not a rewrite.
- Single substrate preserved (PG + AGE + pgvector) — no second graph store (ADR-0007).

**Negative**
- v0 extraction/embedding/retrieval quality is below the eventual ML pipeline; this slice proves
  plumbing + citation grounding, not state-of-the-art retrieval. The held-out F1/P@5 eval gates
  in the L2/L4 READMEs apply to the deferred ML path, not v0.
- Carrying both a deterministic and an ML extraction path is some interface surface to maintain.

**EU sovereignty check**
- v0 makes **no external calls**: deterministic ingest, hashing embeddings, deterministic drafting.
  When the live Claude path is enabled it is Anthropic EU only (ADR-0010). bge-m3/reranker weights
  are mirrored to EU before the production swap (L2/L4 READMEs). ✓

## Alternatives considered
- **Start the LEGAL-BERT corpus/training now** — rejected for the first slice; multi-week, needs
  GPU + annotation, and doesn't reach the drafting DoD. It is the post-MVP production path.
- **Real bge-m3 embeddings in v0** — rejected for now; adds a model dependency + HF download +
  sovereignty caveat with no DoD benefit at this scale. Deferred behind `EmbeddingProvider`.
- **Skip vectors, lexical search only** — rejected; pgvector ANN is core to the LightRAG pattern
  and the substrate is already built (Phase 1 M6). Hashing embeddings keep the vector path real.

## Open questions
- When to start the LEGAL-BERT/Doccano corpus — post-MVP; revisit once the drafting loop has
  real usage to prioritise which obligation types to annotate first.
- Per-claim vs per-draft Context Core granularity — v0 emits one Context Core per cited source;
  finer per-sentence provenance is a v0.1 refinement.

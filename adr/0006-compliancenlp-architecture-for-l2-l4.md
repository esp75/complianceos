# ADR 0006 — ComplianceNLP paper architecture for L2 obligation extraction + L4 gap analysis

**Status**: Accepted — 2026-05-15
**Decision-makers**: Maxime Kadr (solo)

## Context

L2 needs to turn regulatory text (EU Space Act, ISO 24113, ITU Radio Regulations) into machine-actionable obligations. L4 needs to detect gaps between operator policies/evidence and those obligations.

The **ComplianceNLP paper** (Guo et al., arXiv:2604.23585, April 2026, code at https://github.com/bettyguo/ComplianceNLP, Apache-2.0) proposes a multi-task architecture:

- LEGAL-BERT encoder
- Three joint heads:
  1. Regulatory NER over 23 entity types
  2. Deontic modality classification (must/shall/may/should)
  3. Cross-reference resolution
- KG-augmented hybrid retrieval (dense+sparse with KG re-ranking)
- Compliance-gap analysis (embedding similarity + fuzzy type match + LLM gap classification)

Reported metrics on financial regulation (SEC, MiFID II, Basel III): 83.4 end-to-end F1, 87.7 gap-detection F1 at threshold. Evaluation datasets are proprietary; numbers are not externally reproducible.

## Decision

Adopt the **architecture** from the ComplianceNLP paper. Re-implement against Celestia's stack.

- L2 extractor lives at `layers/L2-knowledge-graph/extractors/`. Implements the three-head pipeline.
- LEGAL-BERT is the starting encoder; train space-regulatory adapters (LoRA preferred) on a Celestia-built corpus (see `layers/L2-knowledge-graph/corpus/` for the seed).
- Entity type set extends ComplianceNLP's 23 with space-specific types (Orbital Slot, Satellite Class, Frequency Band, Disposal Maneuver, Conjunction Threshold, etc.).
- Deontic modality classifier uses ComplianceNLP's labels (MUST/SHALL/MAY/SHOULD/MUST_NOT).
- Cross-reference resolution: trained on EU Space Act + ISO 24113 cross-refs.
- Gap analysis at L4 uses the same architecture: embedding similarity + type match + LLM classifier.
- Cite the paper in regulator-facing documentation for methodological provenance.

## Consequences

**Positive**
- Architecture is peer-reviewed (arXiv preprint with code release).
- Multi-task heads share encoder weights — efficient inference.
- Provides a defensibility story: "Architecture follows Guo et al. 2026, retrained on space-regulatory corpus."
- LEGAL-BERT is well-understood by NLP audit teams.

**Negative**
- Trained weights from paper are financial-domain; space transfer requires retraining.
- Building SpaceRegObligation corpus (analog to paper's RegObligation) is a multi-week annotation project.
- Need to mirror evaluation methodology since paper datasets are not released — define a Celestia held-out test set.
- LEGAL-BERT is research-grade; production deployment requires inference engineering.

**EU sovereignty check**
- LEGAL-BERT weights hosted on HuggingFace; mirror to EU storage. Training infrastructure must be EU-hosted (Hetzner GPU instances or similar).

## Alternatives considered

- **accord-nlp** — AEC building-codes-domain, weaker fit. Used instead for RASE annotation schema (ADR-0008 future).
- **Plain GPT-4 with citations** — fails the deterministic-output bar for regulators. Rejected.
- **Pure rule-based regex extraction** — brittle, no obligation modality classification. Rejected.

## Open questions

- Adapter strategy (LoRA vs full fine-tune vs prompt-tune) — benchmark in Phase 3.
- Whether to release the space-reg corpus publicly. Default: no (competitive asset); revisit if it accelerates standards work.

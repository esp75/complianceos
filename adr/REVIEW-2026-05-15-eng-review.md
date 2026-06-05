# /plan-eng-review on ROADMAP.md — 2026-05-15

Conducted manually because the gstack-upgrade-triggered macOS TCC sandbox
blocks the interactive Skill flow's Bash invocations. Findings below mirror
the format /plan-eng-review would produce: architecture, data flow, edge
cases, test coverage, performance.

## Verdict at a glance

ROADMAP.md is **internally consistent** with ARCHITECTURE.md and the 11
ADRs. The 4-phase × 16-week solo schedule is **aggressive but achievable**
if four named risks are mitigated. Three concrete gaps need ADR-level
attention before Phase 1 starts.

## 1. Architecture coherence

### Strengths
- Layer ownership is clean. L1 substrate is theopenlane/core, L3 substrate is
  Orekit, L5 substrate is openmct. Nothing is built that already exists OSS
  with the right license + provenance.
- Stack discipline is preserved: Go ONLY in `external/theopenlane-core/`,
  Java ONLY in `layers/L3-sder-engine/orekit-service/`. Celestia code is
  Python (FastAPI) + TypeScript (Next.js + Vue/openmct plugins).
- ADR-0007 closes the "should we add a second graph store?" loophole that
  the initial resource assessment left ambiguous.

### Issues

**I-1: FastAPI ↔ theopenlane GraphQL contract is undefined.**
ROADMAP Phase 1 deliverable "FastAPI orchestration layer scaffold (proxies
to theopenlane GraphQL)" needs an explicit contract document. Without it:
- BFF endpoints will couple to theopenlane's GraphQL schema directly, which
  drifts with every upstream SHA bump.
- L4 drafting agent will end up issuing GraphQL calls from inside the trust
  layer, mixing concerns.

**Recommendation**: add an ADR-0012 (future, Phase 1 week 1) defining the
FastAPI ↔ theopenlane contract: which entities are exposed, which are
proxied 1:1, which are wrapped, where authorization checks happen
(FastAPI BFF vs theopenlane native OpenFGA).

**I-2: gRPC ↔ REST decision for Orekit service is deferred to Phase 2 but
affects Phase 1 client scaffolding.**
ROADMAP Phase 2 says "gRPC vs REST: default gRPC; benchmark." But the
FastAPI orchestration scaffold (Phase 1) will need to know whether to set
up a `grpcio` client or `httpx`. Deferring this risks rework.

**Recommendation**: lock gRPC in Phase 1 week 1. Benchmark in Phase 2 only
to validate, not to re-decide. Rationale: gRPC's typed contracts + bi-di
streaming match the propagation/conjunction use case better than REST;
benchmark would only flip the decision under extreme latency constraints
that don't apply to L3.

**I-3: openmct plugin authoring path is not scoped for Phase 4.**
ROADMAP Phase 4 says "4 Celestia openmct plugins." This is the largest
unknown in v0.2. openmct's plugin API surface is substantial; learning
curve + UI tokenization for the dual Vue/React design system + auth-cookie
plumbing is plausibly 3 weeks alone.

**Recommendation**: Phase 0.5 (this week or next) — spike a single openmct
plugin ("hello-world reading from one L1 GraphQL endpoint") to de-risk
the Phase 4 estimate. If the spike takes >3 days for one plugin, the Phase 4
"4 plugins" budget is wrong and Phase 4 needs scope reduction.

## 2. Data flow

### Strengths
- ARCHITECTURE.md's two worked examples (ISO 24113 disposal compliance,
  ITU-filing maturity) cleanly traverse L1 → L4 → L3 → L2 → L4 with
  citations.
- Provenance flow (Context Cores → L4 drafting → PAdES signed PDF) maps
  to a single source-of-truth chain a regulator can audit.

### Issues

**I-4: Cross-layer error propagation is not specified.**
What happens when:
- L3 Orekit service is down → L4 needs to return what to L5?
- L1 OpenFGA returns "deny" → L4 must short-circuit before retrieving
  evidence (sensitive data leak risk).
- L2 extractor's confidence is below threshold → L4 drafting must surface
  uncertainty in the PAdES PDF, not paper over it.

**Recommendation**: add error-flow appendix to ARCHITECTURE.md (Phase 1
week 1 deliverable, ~1 page). Codify failure modes with named error codes
and the L5 UI consequence of each.

## 3. Edge cases

### Risks the ROADMAP risk register names
- theopenlane schema break: mitigation = SHA pin + ADR
- Orekit JVM ops: mitigation = stateless service + 5% weekly budget
- openmct + Next.js dual design system: mitigation = shared Tailwind tokens
- SpaceRegObligation corpus annotation: mitigation = solo bootstrap small
- LEGAL-BERT space-transfer: fallback to GPT-4-class with human-in-loop
- EU LLM latency: hybrid mode

### Risks the ROADMAP misses

**M-1: LLM cost overrun during Phase 3 retrieval iteration.**
Iterative L4 retrieval evaluation will burn tokens. With ADR-0010 locking
in Claude-only and prompt caching enabled, expected daily dev cost during
Phase 3 is non-trivial (€10–€40/day depending on iteration intensity).
Budget €600–€2400 across Phase 3 weeks. **Add to ROADMAP risk register.**

**M-2: Annotation Inter-Annotator Agreement (IAA) is solo-build's
weakest link.**
RASE annotation (ADR-0008) targets ≥0.85 Cohen's kappa. Solo annotation
has no second annotator → no IAA measurable. **Mitigation**: contract a
single second annotator for IAA-only on a sampled 50-provision subset
post-bootstrap. Budget €1,500. Add to risk register.

**M-3: openmct + Next.js shared auth session is not de-risked.**
ROADMAP Phase 4 says "OpenFGA enforcement at FastAPI boundary used by
both frontends" but doesn't address how the openmct Vue app and Next.js
React app share a session. Cross-frontend SSO is a known footgun
(token format, refresh, logout propagation, CSRF posture).
**Mitigation**: spike this in Phase 0.5 alongside I-3. Or accept that
v0.2 ships with separate logins per frontend.

## 4. Test coverage

### Strengths
- ROADMAP defines a clear definition-of-done per phase.
- Trust-layer property-based tests (hypothesis) called out from v0.1.

### Issues

**T-1: Held-out evaluation set sources are not specified.**
L2 extractor evaluation needs a held-out test set NOT used for adapter
training. With ~500 annotated provisions total in Phase 3, the
train/dev/held-out split (e.g., 80/10/10 = 400/50/50) is too small for
robust F1 estimates with confidence intervals.

**Recommendation**: target 200 annotations for held-out alone, scale
total corpus toward 700 by end Phase 3 if F1 < 0.8 on first pass.

**T-2: L4 citation-fidelity automated test is not defined.**
"Every claim in a drafting output has a citation" should be a CI gate.
ROADMAP mentions a "citation enforcer" (drafting agent rule) but no test
that verifies the enforcer can't be bypassed.

**Recommendation**: add a test harness using LLM-as-judge over a curated
set of obligations, scoring citation completeness + citation accuracy on
drafted outputs. Add to Phase 3 deliverables.

## 5. Performance

### Strengths
- pgvector + AGE composability is proven; benchmarks exist upstream.
- Orekit propagation is well-characterized (seconds per propagation
  rather than minutes).

### Issues

**P-1: L4 retrieval p99 latency target not stated.**
What's the SLA? Regulator-portal drafting requests can tolerate 30s+
(human is reading a PDF). Operator-dashboard real-time compliance
status checks can NOT tolerate 30s.

**Recommendation**: differentiate retrieval-as-batch (Phase 3 drafting,
≤30s p99) from retrieval-as-realtime (Phase 4 dashboard, ≤500ms p99).
Add to ROADMAP Phase 3 and Phase 4 deliverables.

**P-2: Embedding regeneration cost not budgeted.**
bge-m3 embeddings need regeneration when the L2 corpus updates. With
hundreds of provisions and chunks, this is a real workload. Self-hosted
or HF Inference EU costs.

**Recommendation**: budget €100–€300/month for embedding inference;
add to ROADMAP risk register.

## 6. Skill stack alignment

The 8 cherry-picked skills (rag-architect, prompt-engineer, postgres-pro,
database-optimizer, mcp-developer, fastapi-expert, nextjs-developer,
kubernetes-specialist) map cleanly onto the ROADMAP. **No `vue-expert`,
`go-architect`, or `java-architect` is cherry-picked** — intentional
per ADR-0001/0002/0003 (don't extend Go/Java/Vue beyond the substrate
boundaries). This is consistent.

**Gap**: no `terraform-engineer` or equivalent for Coolify/Hetzner deploy.
The "kubernetes-specialist" skill is the closest fit; verify its content
is applicable to Coolify (likely yes — same Docker patterns) before
relying on it in Phase 4.

## 7. Recommended changes before Phase 1 begins

In priority order:

1. **Add ADR-0012** — FastAPI ↔ theopenlane GraphQL contract (1 page; Phase 1 week 1).
2. **Lock Orekit gRPC** in Phase 1 (not Phase 2) and document a placeholder
   contract.
3. **Schedule Phase 0.5** — openmct hello-world plugin spike + cross-frontend
   auth-session spike. Time-box 3 days. If spike fails, scope-cut Phase 4
   to 2 plugins instead of 4.
4. **Append 3 risks to ROADMAP risk register**: M-1 (LLM cost), M-2 (IAA),
   M-3 (cross-frontend auth).
5. **Append performance SLAs**: P-1 (latency tiers) + P-2 (embedding cost).
6. **Define held-out test set sources** for L2 extractor (T-1) and L4
   citation-fidelity CI gate (T-2).

## 8. Verdict

**APPROVED with the 6 changes above.** The plan is sound. The substrate
choices are the right ones. The risk register needs the 3 additions named
in §3 and the 2 SLA notes named in §5 before Phase 1 commits resources.

Estimated impact of the recommended changes on the 16-week timeline:
+1 week (Phase 0.5 spike) → revised 17-week MVP. Worth it.

## Status

**STATUS: DONE_WITH_CONCERNS**
**REASON**: 6 changes recommended before Phase 1 starts; none of them are
substrate-changing (no ADR reversals required), but skipping the spike
risks a Phase 4 scope miss.
**ATTEMPTED**: Full eng-review walk-through of ROADMAP.md + ARCHITECTURE.md
+ all 11 ADRs.
**RECOMMENDATION**: apply the 6 changes to ROADMAP.md + open ADR-0012;
proceed to Phase 1 in week 1.

## Note: /codex consult not executed

ADR-0001's "dual-language Go service behind FastAPI" was earmarked for a
`/codex consult` second-opinion call. Skipped this session for two reasons:

1. `/codex` shells out to OpenAI's Codex CLI, which is blocked by the
   gstack-v1.39-induced TCC sandbox on `~/Documents/` (the same blocker
   that stopped `/sync-gbrain`'s Bash flow). Re-run after restoring
   Documents folder access.
2. ADR-0010 locks the MVP runtime LLM to Claude only. While `/codex` is a
   build-time tool (not a runtime call), keeping the build-time LLM pure
   to Anthropic during MVP is consistent with the sovereignty narrative.
   `/codex` remains available post-MVP for adversarial reviews of
   non-trust-layer code, per the v0.1 CLAUDE.md rules.

If a second opinion on ADR-0001 is still wanted, the cleanest path is to
ask Claude in a fresh session to argue the opposite ("re-implement
theopenlane data model in FastAPI; reject Go service") and adversarially
score it against this ADR.

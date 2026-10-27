# ADR 0010 — MVP LLM policy: Claude only

**Status**: Accepted — 2026-05-15
**Decision-makers**: Maxime Kadr (solo)
**Resolves**: engineering-log open question #3 ([docs/explanation/engineering-log.md](../docs/explanation/engineering-log.md))

## Context

ADR-0006 and the L4 drafting agent design call for an "EU-jurisdiction LLM endpoint." Multiple candidates exist:

- **Anthropic** offers EU endpoints (Claude API) under EU data-residency.
- **Mistral** is EU-native (Paris) — strongest sovereignty narrative.
- **Self-hosted Llama 3.x** on Hetzner GPU is also EU-jurisdiction but requires non-trivial inference engineering.

Running two LLM providers in the MVP doubles prompt-engineering work, doubles cost-monitoring, doubles evaluation harness work, and forces an immediate failover strategy. For a solo build chasing MVP in 16 weeks, that surface area is expensive.

## Decision

For the **MVP (v0.2.0 → v1.0.0 release)**, L4 drafting agent uses **Claude (Anthropic) only**.

- Provider: Anthropic, EU endpoint (data-residency in EU).
- Default model: latest Claude (currently `claude-opus-4-7` for high-stakes drafting; `claude-sonnet-4-6` or `claude-haiku-4-5-20251001` for cheaper retrieval-grading or classification subtasks).
- Prompt caching enabled per `claude-api` skill guidance.
- All calls go through the `app/api/llm/anthropic_eu.py` thin client (future, Phase 3).

**Mistral is deferred to post-MVP** (≥v1.1.0). The L4 client is designed with a provider-router interface so swapping Mistral in later is a config change, not a rewrite.

**Self-hosted Llama is not in the v0.2 MVP plan**, but the L4 client design keeps it open: same provider-router interface, no Anthropic-specific contracts leak into prompt templates.

## Consequences

**Positive**
- One provider to learn, monitor, optimize, and bill.
- Anthropic EU endpoint satisfies sovereignty rules without compromise.
- Prompt caching meaningfully cuts cost for static system prompts.

**Negative**
- Single-provider dependency. Mitigated by the provider-router interface — but the failover code path is untested in MVP.
- If Anthropic EU has an outage, MVP drafting is degraded with no fallback. Documented risk; acceptable for MVP.
- Loses the "EU-native by default" pitch advantage Mistral would give us with EU regulators.

**EU sovereignty check**
- Anthropic EU endpoint: ✅ EU data-residency confirmed.
- All inference data stays in EU. Prompt caches stored EU-side.

## Future migration

When Mistral is added (post-MVP):
1. Add `app/api/llm/mistral_eu.py` implementing the same provider interface.
2. Add per-Organization provider preference in L1 (theopenlane Organization metadata).
3. A/B test on a documented evaluation harness; ship only if Mistral matches Claude quality on the L4 evaluation set.
4. Update this ADR to "Superseded by ADR-XXX."

## Alternatives considered

- **Both Anthropic + Mistral from day 1** — doubles MVP surface area; rejected as solo-build risk.
- **Mistral only** — strongest sovereignty story but Mistral's prompt-caching, tool-use, and long-context behavior are less mature than Claude's for the citation-grounded drafting use case; risk to MVP quality. Rejected.
- **Self-hosted Llama from day 1** — multi-week inference engineering pre-Phase 3; rejected as out of scope.

## Open questions

- Specific Anthropic EU endpoint URL + API key management — wire up via `app/api/secrets/` in Phase 3.
- Whether to disable any cross-region traffic flags on the Anthropic client — confirm with Anthropic EU documentation before Phase 3 build.

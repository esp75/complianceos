# ComplianceOS — agent instructions

## Product

ComplianceOS is an open-source regulatory path planner for satellite operators, maintained by
Tidelink. Given a mission, it works out which licences, authorisations and ITU filings are needed
in each country, why (citing the law), in what order and by when, and tracks the applications.
It stands on Apache-2.0 substrates (theopenlane/core, Orekit, openmct) and an open, cited
knowledge pack (`knowledge/`, ADR-0018). Citation-grounded drafting over Postgres + Apache AGE +
pgvector. Multi-tenant team mode via OpenFGA; single-user local mode by default. Ed25519 signing +
Merkle audit chain for exported evidence and dossiers.

## Sovereignty rules — non-negotiable (carried from v0.1)

- EU-only infrastructure. Hetzner (Germany) for compute, EU-resident managed Postgres for production data.
- No US-hosted services for application data or identity. No Supabase as backend, no Vercel hosting, no Auth0/Clerk, no Snowflake/Databricks.
- PGLite (local SQLite-on-Postgres) for gstack agent memory. Never Supabase.
- For LLM calls, prefer EU-jurisdiction endpoints. Document any US LLM call in `docs/THREAT_MODEL.md` under "Documented US LLM dependencies".
- Trust-layer files — `app/api/trust/**`, `app/api/rls/**`, `app/api/bundle/sign*.py` — are reserved for paid external review. Do NOT run `/codex` on them. They are marked with a header comment `# MARKED-FOR-EXTERNAL-REVIEW`.

## v0.2 substrate rules

- **theopenlane/core is vendored, not forked-to-GitHub.** Live in `external/theopenlane-core/` at pinned SHA. Extensions live in `layers/L1-substrate/extensions/` and reference the upstream via interface contracts, not by editing upstream files.
- **Orekit runs as a JVM microservice in its own container.** Python clients use a thin gRPC or REST wrapper. Never link Java code into the FastAPI process.
- **openmct is the operator-facing dashboard host. Next.js 14 remains the insurer/regulator portal host.** Two frontends, one auth layer (OpenFGA). See ADR-0003.
- **No second graph store.** Postgres + AGE + pgvector is the production KG. gbrain stays at agent-memory layer only. Do not introduce Neo4j, Cassandra, Qdrant, or Pulsar.
- **Pattern adoption, not runtime adoption** for LightRAG, trustgraph, ComplianceNLP — re-implement their algorithms against the Postgres stack.
- **MVP LLM policy: Claude only** (Anthropic EU endpoint). Mistral and self-hosted Llama are post-MVP options behind the same provider-router interface. See [ADR-0010](./adr/0010-mvp-llm-policy-claude-only.md). The MVP drafting agent runtime never calls any non-Anthropic LLM.
- **External security review vendor**: Quarkslab (FR) primary, Cure53 (DE) backup. See [ADR-0011](./adr/0011-external-security-review-quarkslab.md). Phase 5 (post-MVP, weeks 17–20). Trust-layer code frozen with a `pre-audit-v0` git tag before review begins.

## File-marking convention (carried from v0.1)

Every file under `app/api/trust/**`, `app/api/rls/**`, and `app/api/bundle/sign*.py` must start with:

```
# MARKED-FOR-EXTERNAL-REVIEW — Trail of Bits / Quarkslab / Cure53
```

Files with this header are excluded from `/codex` (which would forward content to OpenAI, a US-jurisdiction provider). They may only be edited by Claude Code running on EU-jurisdiction Anthropic endpoints, and every edit must be reviewed in PR before merge.

## Coding conventions (carried from v0.1)

- Python 3.12, FastAPI, pydantic v2.
- Next.js 14 App Router, TypeScript strict, Tailwind, shadcn/ui.
- openmct host: Vue 3 (as upstream openmct ships). Treat as a separate frontend bundle, not a target for Next.js conversion.
- Go 1.22 ONLY inside `external/theopenlane-core/` (the vendored substrate). Celestia code is never Go.
- Java 21 ONLY inside `layers/L3-sder-engine/orekit-service/` (the Orekit microservice). Celestia code is never Java.
- Lint: ruff (Python), eslint + prettier (TS). Type-check: mypy `--strict` (Python), `tsc --noEmit` (TS).
- Tests: pytest for backend, hypothesis for property-based tests on trust-layer code.
- Dependency management: `uv` for Python, `bun` for the Next.js apps.

## gstack workflow (carried from v0.1 + v0.2 additions)

- Every working session opens with `/context-restore` and closes with `/context-save` and `/retro`.
- `/careful` is mandatory inside `app/api/trust/`, `app/api/rls/`, `app/api/bundle/`.
- `/cso` runs on every PR that touches auth, ingest, rag, trust, rls, or bundle paths.
- For broad codebase work prefer the gstack `/investigate` (Iron Law: no fixes without root cause) before reaching for `/codex` or one-shot fixes.
- **v0.2 addition**: Before modifying anything in `external/`, write an ADR documenting the divergence and pin the new SHA.
- **v0.2 addition**: Before adopting any new MCP server, run `/cso` on the supply-chain risk first.

## Cherry-picked Claude skills (`.claude/skills/`)

8 skills cherry-picked from Jeffallan/claude-skills:
- **rag-architect** — citation-grounded retrieval design (L4)
- **prompt-engineer** — LLM prompt design (L4)
- **postgres-pro** — Postgres 17 + AGE patterns (L2)
- **database-optimizer** — KG query optimization (L2)
- **mcp-developer** — extending gbrain MCP (agent memory)
- **fastapi-expert** — FastAPI patterns (L1/L4 API)
- **nextjs-developer** — Next.js 14 patterns (L5 portal)
- **kubernetes-specialist** — Hetzner+Coolify orchestration (cross-cutting)

## Reference docs

Strategic background and the original build plan live outside this repository on purpose, so they
don't become part of the audit-reviewed surface.

## Quick reference

- Architecture: [`ARCHITECTURE.md`](./ARCHITECTURE.md)
- Roadmap: [`ROADMAP.md`](./ROADMAP.md)
- Design system: [`DESIGN.md`](./DESIGN.md)
- ADRs: [`adr/`](./adr/)
- Layer specs: [`layers/*/README.md`](./layers/)
- Vendor pins: [`external/VENDOR.md`](./external/VENDOR.md)
- License matrix: [`docs/license-matrix.md`](./docs/license-matrix.md)
- Current status: [`STATUS.md`](./STATUS.md)

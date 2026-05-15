# Celestia Dynamics — complianceOS

## Product

Celestia Dynamics is an EU-sovereign regulatory compliance SaaS for satellite operators. The stack is Postgres 17 + Apache AGE + pgvector + FastAPI + Next.js 14, deployed on Hetzner via Coolify, with ed25519 signing + Merkle audit chain, multi-tenant Postgres RLS, citation-forced RAG over a reg-graph knowledge graph, and signed PAdES PDF evidence bundles for regulators. Solo build, ~5–6 months to paying-customer-quality MVP, €18–34k cash including a paid external security review at Phase 5.

## Sovereignty rules — non-negotiable

- EU-only infrastructure. Hetzner (Germany) for compute, EU-resident managed Postgres for production data.
- No US-hosted services for application data or identity. No Supabase as backend, no Vercel hosting, no Auth0/Clerk, no Snowflake/Databricks.
- PGLite (local SQLite-on-Postgres) for gstack agent memory. Never Supabase.
- For LLM calls, prefer EU-jurisdiction endpoints. Document any US LLM call in `docs/THREAT_MODEL.md` under "Documented US LLM dependencies".
- Trust-layer files — `app/api/trust/**`, `app/api/rls/**`, `app/api/bundle/sign*.py` — are reserved for paid external review. Do NOT run `/codex` on them. They are marked with a header comment `# MARKED-FOR-EXTERNAL-REVIEW`.

## File-marking convention

Every file under `app/api/trust/**`, `app/api/rls/**`, and `app/api/bundle/sign*.py` must start with:

```
# MARKED-FOR-EXTERNAL-REVIEW — Trail of Bits / Quarkslab / Cure53
```

Files with this header are excluded from `/codex` (which would forward content to OpenAI, a US-jurisdiction provider). They may only be edited by Claude Code running on EU-jurisdiction Anthropic endpoints, and every edit must be reviewed in PR before merge.

## Coding conventions

- Python 3.12, FastAPI, pydantic v2.
- Next.js 14 App Router, TypeScript strict, Tailwind, shadcn/ui.
- Lint: ruff (Python), eslint + prettier (TS). Type-check: mypy `--strict` (Python), `tsc --noEmit` (TS).
- Tests: pytest for backend, hypothesis for property-based tests on trust-layer code.
- Dependency management: `uv` for Python, `bun` for the Next.js app.

## gstack workflow

- Every working session opens with `/context-restore` and closes with `/context-save` and `/retro`.
- `/careful` is mandatory inside `app/api/trust/`, `app/api/rls/`, `app/api/bundle/`.
- `/cso` runs on every PR that touches auth, ingest, rag, trust, rls, or bundle paths.
- For broad codebase work prefer the gstack `/investigate` (Iron Law: no fixes without root cause) before reaching for `/codex` or one-shot fixes.

## Reference docs

Strategic background and the source-of-truth build plan live outside this repo at:

```
~/Documents/CLAUDE COWORK/OUTPUTS/celestia-solo-build-plan/
  SOLO_BUILD_PLAN.md
  GSTACK_REASSESSMENT.md
  OSS_STACK.md
  INSTALL_PROMPT.md
```

If those files move, update this path. They are intentionally outside the repo so they don't become part of the audit-reviewed surface.

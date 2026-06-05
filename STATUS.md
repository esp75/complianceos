# STATUS — ComplianceOS v0.2

**Date**: 2026-06-05
**Phase**: 1 (L1 substrate) — M0–M4 DONE
**Working dir**: `/Users/esponsor/Documents/Github/complianceOSv0.2/`
**Scope**: Phase 0 scaffolding complete. Phase 1 underway: the L1 substrate now boots
locally and the Celestia BFF proves connectivity to it.

## Phase 1 progress (L1 substrate)

Repo is now git-initialized (branch `phase1-l1-substrate-first-slice`). Docker runtime:
**colima** (local dev).

- ✅ **M0** — prerequisites: colima + Docker, git init, `app/` (uv, Python 3.12), **ADR-0012**
  (FastAPI↔theopenlane GraphQL contract).
- ✅ **M1** — infra up + BFF health proxy: `cross-cutting/deploy/docker-compose.yml`
  (postgres, openfga, redis, core@v1.20.6, riverboat, dex) + Celestia FastAPI BFF (`app/`).
  Verified: core `/ready` 200 (all subsystems OK), BFF `/readyz` 200 (503 when core down),
  pytest green. See [docs/upstream-watch.md](./docs/upstream-watch.md) for image pins +
  dev-only deviations (core-as-root for key gen, riverboat placeholder token).
- ✅ **M2** — auth + OpenFGA tetrad: email/password auth (Dex SSO deferred to Phase 4 —
  needs per-org enforcement), BFF `/auth/me` + `/auth/can`, and the operator/insurer/
  regulator/admin tetrad via OpenFGA groups + tuples (ADR-0012). `seed_tetrad.py` verifies
  8/8 role checks. `/cso` daily: 0 critical/high, 1 medium (committed dev session keys —
  inject before prod). Env: core is amd64-only → colima must run VZ+Rosetta. BFF on :8001.
- ✅ **M3** — framework loader: hand-authored ISO 24113 (§6.1–6.4) + ITU RR (Art.9/11/21/22)
  YAMLs in the `openlane.io/v1` schema; `app/app/loaders/{schema,framework_loader}.py`
  transform Framework→`createStandard`, Control→`createControl`, `spec.controls[]`→
  `createSubcontrol` (RASE/deontic carried in `descriptionJSON`; cross-refs in
  `mappedCategories`). Loaded all 3 frameworks (13 controls, 22 subcontrols), idempotent.
  theopenlane's `@externalReadOnly(source:FRAMEWORK)` skips creates, so title/refCode/etc.
  set fine on create. Evidence types are a BFF tag vocabulary (not pushed). 15 tests green.
- ✅ **M4** — BFF domain endpoints with tetrad enforcement (ADR-0012): `GET /frameworks`,
  `GET /organizations`, `POST /evidence`, `GET /evidence?org_id=`, `GET /evidence/{id}/history`.
  Each gates on an OpenFGA `assert_can` check at the boundary (fail-closed), then forwards the
  user token for defense-in-depth. Verified live: operator creates evidence linked to a control
  (201), insurer blocked (403), regulator lists + reads audit history (200), operator denied
  history (403). Seed now mints per-role PATs. 20 tests; mypy/ruff clean. `/cso`: 0 findings.
- ⏳ **Next**: M5 — end-to-end smoke test (`tests/test_smoke_e2e.py`) + minimal regulator portal
  stub (login → evidence list → download audit history). M6 (optional): KG Postgres for Phase 3.

## What was scaffolded

### Top-level docs (8 files)
- `LICENSE` (Apache-2.0)
- `VERSION` (0.2.0)
- `README.md` — entry point with layer table + adoption rationale
- `CLAUDE.md` — sovereignty rules + substrate rules + cherry-picked-skills inventory
- `ARCHITECTURE.md` — 5 layers + cross-cutting, full data flow examples, resource-to-layer mapping
- `ROADMAP.md` — 4 phases × ~16 weeks, deliverables + tools per phase, risk register
- `DESIGN.md` — design tokens, audience-specific surfaces, anti-patterns
- `CHANGELOG.md` — v0.2.0 "Stand on Giants" release notes

### ADRs (9 files under `adr/`)
- 0001 — Fork theopenlane/core as L1 substrate
- 0002 — Orekit as JVM microservice for L3
- 0003 — openmct for operator dashboard + Next.js for insurer/regulator portals
- 0004 — LightRAG dual-level retrieval pattern over Postgres+AGE+pgvector
- 0005 — trustgraph Context Cores pattern only (no Cassandra/Pulsar runtime)
- 0006 — ComplianceNLP paper architecture for L2 + L4
- 0007 — Postgres+AGE+pgvector as production KG substrate
- 0008 — accord-nlp RASE annotation schema
- 0009 — Port ITU-Compliance-Assessment-Monitor SNL + filing-maturity

### Layer scaffolds (6 READMEs under `layers/`)
- L1-substrate/ with `frameworks/{eu-space-act,iso-24113,itu}/` + `extensions/`
- L2-knowledge-graph/ with `ontology/`, `extractors/`, `corpus/`, `ingest/`
- L3-sder-engine/ with `orekit-service/`, `ostk-explore/`, `itu-compliance/`, `risk-scoring/`
- L4-drafting-agent/ with `retrieval/`, `provenance/`, `extraction/`, `drafting/`
- L5-dashboard/ with `openmct-host/`, `plugins/`
- cross-cutting/ with `auth/`, `observability/`, `deploy/`

### Documentation (2 files under `docs/`)
- `license-matrix.md` — every dep, license, AGPL/GPL rejection list, model + LLM endpoint sovereignty plan
- `dependency-map.md` — Celestia source path → upstream code; Layer ↔ ADR mapping; versioning policy

### Vendored upstreams (10 repos, 920 MB under `external/`)
All pinned in `external/VENDOR.md`:

| Dep | License | SHA | Size |
|---|---|---|---|
| theopenlane-core | Apache-2.0 | a76ccb5c | 178M |
| orekit | Apache-2.0 | fb3a845c | 157M |
| ostk | Apache-2.0 | 1eaf348f | 99M |
| openmct | Apache-2.0 | 3aaa0f05 | 14M |
| lightrag | MIT | 405525a5 | 23M |
| trustgraph | Apache-2.0 | 159b1e28 | 35M |
| compliance-nlp | Apache-2.0 | 8a85f38a | 516K |
| accord-nlp | Apache-2.0 | f1bc2310 | 28M |
| itu-compliance-monitor | MIT | d8bf1b44 | 387M |
| jeffallan-skills | MIT | 5e8b6b8f | 9.8M |

`external/` is in `.gitignore`; reconstitute via `scripts/bootstrap.sh`.

### Cherry-picked Claude skills (8 under `.claude/skills/`)
From `external/jeffallan-skills/skills/`:
- `rag-architect` (L4)
- `prompt-engineer` (L4)
- `postgres-pro` (L2)
- `database-optimizer` (L2)
- `mcp-developer` (cross-cutting)
- `fastapi-expert` (L1, L4)
- `nextjs-developer` (L5)
- `kubernetes-specialist` (cross-cutting)

### Bootstrap tooling (3 scripts under `scripts/`)
- `bootstrap.sh` — reconstitute `external/` at pinned SHAs (idempotent)
- `vendor-update.sh` — propose an upstream SHA bump (manual review required)
- `ingest-to-gbrain.sh` — documents the gbrain page+link set; actual ingest runs in-session

### Claude Code config (`.claude/settings.json`)
- Skill allowlist for the 8 cherry-picks
- Permission allowlist for dev commands
- Permission denylist for destructive ops (rm -rf /, force-push, hard reset)
- `guard.no-codex-on` glob list for trust-layer files
- `guard.external-review-marker` set to `# MARKED-FOR-EXTERNAL-REVIEW`

### gbrain ingestion (16 pages, ~30 links)
Pages: `complianceos-overview`, `layer-l1-substrate` … `layer-cross-cutting` (7), `adr-0001` … `adr-0009` (9).

Link types established:
- `complianceos-overview` → each layer (`contains`)
- Each layer → its governing ADR(s) (`governed_by`)
- Each ADR → the layer(s) it affects (`affects`)

Brain score: 50 (capped at 50 in this pass because embedding generation runs async on the gbrain backend — pages have content, embeddings will populate on `/sync-gbrain`).

## What is explicitly NOT done (and why)

- **`/gstack-upgrade`** not yet invoked — left for the user to run interactively to pull `/document-generate` + `/connect-chrome` upstream drift.
- **`/plan-eng-review` / `/codex` / `/cso` reviews** not run — these are interactive skills that benefit from real-time user choice on ambiguous flags. Recommended order: `/plan-eng-review` on ROADMAP.md → `/codex` on ADR-0001 + ADR-0002 + ADR-0007 (substrate decisions worth a second opinion) → `/cso` on the license matrix + dependency map.
- **`/sync-gbrain`** not yet invoked — run this to populate embeddings (currently 0/16) and update agent search guidance in CLAUDE.md.
- **Phase 1 code** — no Go theopenlane wiring, no FastAPI orchestration, no docker-compose, no OpenFGA model. Per scope ladder.

## Sovereignty + trust-layer compliance

- ✅ EU-only deploy plan documented (Hetzner DE, Coolify, Hetzner-managed Postgres).
- ✅ `MARKED-FOR-EXTERNAL-REVIEW` convention carried from v0.1; recorded in `.claude/settings.json` and CLAUDE.md.
- ✅ No US-hosted-services dependencies in vendored upstreams (all self-hostable).
- ⚠️ LEGAL-BERT + BAAI/bge-* model weights live on HuggingFace; mirror to EU storage in Phase 3 prep (tracked in `docs/license-matrix.md`).
- ⚠️ Drafting LLM endpoints — EU jurisdiction (Anthropic EU + Mistral) preferred; any US fallback must be documented per v0.1 rules.

## Next 3 concrete tasks

1. **Run `/gstack-upgrade` interactively** to absorb upstream drift, then `/sync-gbrain` to populate embeddings and refresh CLAUDE.md search guidance.
2. **Open `/plan-eng-review` on ROADMAP.md** — surface architecture conflicts before Phase 1 starts. Pair with `/codex consult` on the Go-service-behind-FastAPI shape (ADR-0001 dual-language risk).
3. **Hand-author the EU Space Act Framework YAML** under `layers/L1-substrate/frameworks/eu-space-act/`. Start with Articles 1–5 (definitions + scope) — small enough to validate the Openlane Framework schema end-to-end before scaling.

## Open questions — RESOLVED 2026-05-15

1. **Go-service-behind-FastAPI** → ✅ Keep ADR-0001 as accepted. Dual-language commitment stands.
2. **openmct + Next.js dual frontend** → ✅ Keep dual. ADR-0003 stands.
3. **EU LLM endpoint plan** → ✅ Confirmed: both Anthropic-EU and Mistral are acceptable EU-sovereign options. **For MVP only Claude is used** as runtime LLM. Mistral is deferred to post-MVP behind a provider-router interface. See [ADR-0010](./adr/0010-mvp-llm-policy-claude-only.md).
4. **ComplianceNLP retraining** → ✅ Solo-bootstrap small (100-provision) corpus first. Contracted-annotator option remains documented in ROADMAP risk register for Phase 3 expansion if solo bandwidth blocks.
5. **External-review vendor** → ✅ **Quarkslab (FR) primary, Cure53 (DE) backup.** Decision rationale and Phase 5 prep checklist in [ADR-0011](./adr/0011-external-security-review-quarkslab.md). Trail of Bits dropped (US-jurisdiction conflict with EU sovereignty narrative).

## How to resume

Future Claude session: `cd /Users/esponsor/Documents/Github/complianceOSv0.2 && claude` — CLAUDE.md and `.claude/settings.json` will brief the next session. To navigate the architecture, search gbrain for `complianceos-overview` and traverse from there.

## How to nuke and start over

`rm -rf external/` then `./scripts/bootstrap.sh` reconstitutes the vendored deps. Everything else is committed-able source under git.

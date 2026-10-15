# STATUS — ComplianceOS v0.2

**Date**: 2026-07-23
**Phase**: STRATEGIC REFOCUS (ADR-0017) → Phase P1 of the new ROADMAP not yet started

## 2026-07-23 — First-product refocus (ADR-0017)

The first product is now **AI regulatory-affairs for satellite operators** (Market-Access
Dossier → the Watch → program of record), pilot-first GTM. Full analysis lives outside the
repo (audit-surface rule).

- **Carries:** L1 substrate + tetrad, L2 KG + ingest (re-targeted at national telecom/space
  acts), L4 retrieval/drafting/citation-enforcer (becomes the dossier engine), trust layer
  (signed deliverables + program history; Quarkslab plan unchanged).
- **Parks:** L3 SDER (Orekit, ITU proximity, risk scoring) and L5 openmct host/plugins —
  code retained, containers shelved; revisit triggers in ADR-0017.
- **Next:** ROADMAP Phase P1 (dossier pipeline for first pilot jurisdictions), gated on
  pilot signups from the sales sprint (assets outside repo).
- ROADMAP.md rewritten around the new product; sections below this line are the historical
  record of the pre-refocus build (all foundation slices remain complete and reusable).

---

**Historical scope note (pre-refocus)**: Phase 0 + Phase 1 (L1) + Phase 2 (L3 SDER) + Phase 3 first slice complete. Phase 4
first slice: the openmct operator dashboard has a host scaffold and a data-backed
Compliance Status panel fed by a new BFF rollup endpoint. All on branch `phase2-l3-sder-first-slice`.

## Phase 4 progress (L5 operator dashboard)

First slices landed: the openmct host scaffold + the **Compliance Status panel** (ADR-0015), and the
**trust/bundle first slice** (ADR-0016) — a self-verifying signed compliance bundle over
`POST /bundle/sign`. The other three plugins (evidence widget, ITU tracker, conjunction strip), the
Next.js portal, full PAdES + EU-KMS keys, and Hetzner/Coolify deployment are deferred to later
Phase-4 slices. Headless/offline discipline (ADR-0014): proven by pytest + `bun test` +
`bun run build`, no browser, no deploy.

- ✅ **P0** — **ADR-0015** (openmct first-slice scope: panel-over-BFF-rollup, headless proof,
  deferrals).
- ✅ **P1** — BFF rollup endpoint `GET /compliance/status?org_id=` (`app/app/api/compliance.py`),
  gated by `can_view` (ADR-0012). The Standards×Evidence join lives server-side in a pure,
  unit-tested module (`app/app/l5/rollup.py`): per-Framework/per-Control status
  (compliant / partial / not_assessed by evidence presence) + org summary. 6 tests.
- ✅ **P2** — openmct host scaffold (`layers/L5-dashboard/openmct-host/`): installs vendored
  openmct (external at build time, ADR-0003) + the Celestia plugin; runtime config via
  `window.CELESTIA`. `bun run build` green.
- ✅ **P3** — Compliance Status plugin (`layers/L5-dashboard/plugins/compliance-status/`):
  Vue 3 panel (render-function, mission-control idiom) + framework-free `api.js` (BFF adapter)
  + `transform.js` (rollup→view-model). 11 headless unit tests; `bun run build` green.
- ✅ **P4** — Trust/bundle first slice (**ADR-0016**): `POST /bundle/sign?org_id=` returns a
  self-verifying signed compliance bundle PDF. Per-Org Ed25519 keys HKDF-derived from a master
  seed (`app/app/api/trust/keys.py`, `keystore.py`); pure SHA-256 Merkle seal + cross-bundle
  tamper-evident chain (`merkle.py`, `store.py`); detached Ed25519 signature over a canonical
  manifest (`signing.py`, `bundle/manifest.py`); deterministic PDF embedding a verifiable sidecar
  (`bundle/sign_pdf.py`, fpdf2) behind a `BundleSigner` seam. Marked `MARKED-FOR-EXTERNAL-REVIEW`
  (Quarkslab, ADR-0011); a header-presence guard test enforces the marking. Headless/offline:
  ruff + mypy --strict clean, +27 tests (merkle/keys/signing/manifest/endpoint/guard). Threat
  model: `docs/THREAT_MODEL.md`. Full PAdES-B-LT + EU-KMS keys deferred (pre-audit, same seams).

**Deferred (later Phase-4 slices)**: evidence-submission / ITU-maturity / conjunction-alarm
plugins, control→evidence drill-down + sub-control `evidence_required` coverage, Next.js
insurer/regulator portal, full PAdES-B-LT + EU-KMS keys + `can_export_bundle` relation,
OpenFGA-at-boundary hardening + Postgres RLS (`app/api/rls/**`), Hetzner/Coolify deploy,
browser/visual QA (`/design-review`, `/qa`).

## Phase 3 progress (L2 knowledge graph + L4 drafting agent)

First slice (ADR-0014): Claude-as-extractor MVP — deterministic ingest of the loaded
frameworks for the DoD, LEGAL-BERT/Doccano corpus deferred; v0 hashing embeddings (bge-m3
swap behind the interface); LightRAG retrieval minus the reranker; drafting behind a
provider-router LLM interface with a deterministic offline path (no key, no US LLM call).

- ✅ **P0** — **ADR-0014** (Claude-as-extractor scope, deferrals, offline-by-default) +
  `RASE-celestia.md` ontology + KG schema (Obligation/EvidenceType nodes, CITES/REQUIRES_EVIDENCE
  edges, `obligation_embedding` vector(384), `context_core` table).
- ✅ **P1** — KG client (`app/app/clients/kg.py`): pgvector ANN + AGE Cypher traversal +
  Context Core tables; deterministic dim-384 hashing embedding. Fixed the AGE-under-asyncpg
  search_path-reset gotcha. Lifespan connects tolerantly (`kg` profile); `/readyz` reports kg.
- ✅ **P2** — L2 ingest (`app/app/kg/ingest.py`) materializes the loaded ISO 24113 / ITU /
  EU Space Act YAMLs into the KG (13 obligations / 3 frameworks, verified live). LLM
  provider-router (`app/app/llm/`, Anthropic EU, ADR-0010) + Claude-extractor for raw text.
  Endpoints `POST /kg/ingest`, `POST /kg/extract`, `GET /kg/obligations` (pgvector ANN).
- ✅ **P3** — L4 dual-level retrieval (`app/app/l4/retrieval.py`): pgvector ANN (local) + AGE
  CITES traversal (global) + fusion; reranker deferred. Context Core provenance
  (`app/app/l4/provenance.py`): one core per cited source.
- ✅ **P4** — L4 drafting (`app/app/l4/drafting.py`) + citation enforcer (`citations.py`,
  >=2 obligations + >=1 evidence, each Context-Core-backed; ungrounded draft 422s) + `POST
  /draft/obligation`. **Phase-3 DoD met live**: a regulator question returns a paragraph citing
  4 obligations (incl. EU-SA Art.3 via the global CITES traversal) + 3 evidence records (the
  Phase-2 conjunction_report + Phase-1 disposal telemetry), each with a Context Core. e2e 3/3.

**Phase 3 first slice complete.** Deferred (post-MVP): LEGAL-BERT 3-head pipeline + Doccano
corpus (ADR-0006/0008), bge-m3 embeddings + bge-reranker, live Anthropic EU drafting, PAdES
signing + trust-marking the drafting code. Next per ROADMAP: Phase 4 (L5 dashboards, EU IdP,
production hardening) — see `docs/upstream-watch.md`.

## Phase 2 progress (L3 SDER engine)

Branch `phase2-l3-sder-first-slice`. Plan: full DoD vertical slice M0–M7 (Orekit REST
service → Python client → ITU GEO proximity port → risk-scoring v0 → conjunction Evidence
write-back → portal panel + e2e). Transport decision: **REST/JSON** (ADR-0013).

- ✅ **M0** — **ADR-0013** (Orekit service contract: REST/JSON for v0, gRPC deferred behind a
  Phase-3 benchmark; resolves ADR-0002's open question) + `layers/L3-sder-engine/orekit-service/CONTRACT.md`
  (endpoint JSON shapes, units km/km·s⁻¹, frames EME2000/ITRF/TEME, error envelope). Pinned the
  running jar to released `org.orekit:orekit:13.1.5` (vendored source is 14.0-SNAPSHOT on develop);
  skew recorded in `docs/upstream-watch.md`. Conjunction v0 = sampled min-miss-distance (no Pc).
- ✅ **M1** — Orekit service skeleton: Java 21 / Spring Boot under
  `layers/L3-sder-engine/orekit-service/` (the only Java in the repo). `OrekitDataConfig` loads
  runtime-mounted `/orekit-data` and gates `/readyz`; `/healthz` is liveness-only; uniform error
  envelope; multi-stage JRE-only Dockerfile; `fetch-orekit-data.sh` (data mounted, not baked in).
  Verified in-container: 3/3 health tests, orekit 13.1.5 + Spring Boot 3.3.5 resolve.
- ✅ **M2** — Endpoints `propagate` / `conjunction` / `frame_convert` (logic in services, out of
  controllers). Conjunction = sampled minimum-miss-distance (local minima below threshold; not Pc).
  Verified with real orekit-data: 11/11 tests, 0 skipped — ISS radius ~6780 km, self-conjunction
  miss ~0, frame rotation preserves position magnitude. Fixed data-fetch URL (branch is `main`).
- ✅ **M3** — `orekit` service in `docker-compose.yml` behind `profiles:[sder]` (orekit-data volume,
  curl healthcheck, on `celestia-l1`). Verified live: container healthy, `/readyz` ready, ISS
  `/propagate` ~6720 km, self-`/conjunction` 0.0 km, bad TLE → 400 envelope.
- ✅ **M4** — `app/app/clients/orekit.py` (`OrekitClient` on the shared httpx transport, mirrors
  `openlane.py`) + `CELESTIA_OREKIT_BASE_URL` config + lifespan/deps wiring; `/readyz` reports
  orekit informationally (does not gate). 6 client unit tests (httpx MockTransport).
- ✅ **M5** — ITU compliance port (`layers/L3-sder-engine/itu-compliance/`, ADR-0009): typed
  filing-maturity FSM (early/late/brought-into-use/suspended + Postgres ENUM DDL), stdlib-csv SNL
  parse + httpx fetch (refactored off the upstream `os.system`/pandas), GEO longitudinal proximity
  with antimeridian wraparound; LEO/MEO/HEO raise `RegimeNotSupportedError` (deferred). 21 tests.
- ✅ **M6** — Risk-scoring v0 (`layers/L3-sder-engine/risk-scoring/`): `METHODOLOGY.md` (stub, "not
  insurer-grade" disclaimer) + deterministic `score_satellite` → 0–100 score + band + weighted
  breakdown. Decoupled from itu-compliance. 7 tests (boundary, monotonicity, bands).
- ✅ **M7** — `/sder/conjunction-check` (tetrad-gated, operator/admin) wires Orekit conjunction +
  ITU proximity + risk score and writes a `conjunction_report` Evidence via the L1 `createEvidence`
  path (ADR-0012) linked to ISO 24113 §6.4; `/sder/risk-score` calculator; operator risk panel on
  `portal.html`. App image now builds from repo root to install the L3 packages as uv path deps
  (py.typed added); root `.dockerignore`. 6 router unit tests; **Phase-2 DoD e2e (2/2) passes**:
  operator TLE → Orekit (live JVM) → ITU proximity → risk 50/medium → Evidence linked to ISO 24113
  §6.4, regulator sees it + audit history, insurer blocked. mypy --strict + ruff clean throughout.

**Phase 2 (L3 SDER engine) first slice complete.** The L3 DoD is demonstrated end to end. Next per
ROADMAP: Phase 3 (L2 knowledge graph + L4 drafting agent). Deferred from this slice: OSTk notebooks,
LEO/MEO/HEO ITU logic, probability-of-collision, gRPC transport (Phase-3 benchmark), external TLE
feed auto-fetch, real openmct operator portal (Phase 4), risk-score actuarial review.

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
- ✅ **M5** — DoD smoke test + regulator portal stub. `tests/test_smoke_e2e.py` (opt-in,
  `CELESTIA_E2E=1`) drives the BFF as all four roles and asserts the DoD; passes against the
  live stack. `GET /portal` serves a self-contained dev stub (real portal = Next.js, Phase 4):
  paste a regulator PAT + org → load evidence → download a record's audit history. Verified in
  a browser end to end.
- **Phase 1 DoD met**: a regulator authenticates, sees an Organization's evidence list, and
  downloads an Evidence record's audit history (createdBy = the operator who created it).
- ✅ **M6** — `kg-postgres`: Postgres 17 + **Apache AGE 1.7.0** + **pgvector 0.8.2** in one image
  (`cross-cutting/deploy/Dockerfile.kg-postgres`, pgvector base + AGE compiled from source), gated
  behind compose `profiles:[kg]`, separate from theopenlane's operational DB. Verified both
  extensions load and a starter graph `celestia_kg` + a vector both work. De-risks Phase 3;
  validates ADR-0007 on PG17/arm64. Not yet populated.

**Phase 1 (L1 substrate) is complete.** Next milestone is Phase 2 — L3 SDER engine (Orekit
JVM microservice + ITU SNL ingestion); see ROADMAP.md. Carry-forward items for Phase 4 are in
`docs/upstream-watch.md` (dev-only deviations, EU IdP, Next.js portal, secret injection).

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

Future Claude session: open the repository root in Claude Code — CLAUDE.md and `.claude/settings.json` will brief the next session. To navigate the architecture, search gbrain for `complianceos-overview` and traverse from there.

## How to nuke and start over

`rm -rf external/` then `./scripts/bootstrap.sh` reconstitutes the vendored deps. Everything else is committed-able source under git.

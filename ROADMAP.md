# ComplianceOS v0.2 — Roadmap

4 phases over ~16 weeks. Solo build assumption; multiply by ~1.5–2 for team-of-2.

## Phase 0 — Bootstrap (week 0, this scaffold)

- [x] Folder skeleton + ADRs + docs
- [x] 9 vendored upstream deps pinned in `external/VENDOR.md`
- [x] 8 cherry-picked Jeffallan skills in `.claude/skills/`
- [x] gbrain ingestion of the architecture for agent navigation
- [ ] `/gstack-upgrade` to pull `/document-generate` + `/connect-chrome` drift (run before Phase 1)
- [ ] `/cso` security review of dependency choices and license matrix
- [ ] `/plan-eng-review` on this ROADMAP before starting Phase 1

## Phase 1 — L1 substrate (weeks 1–4)

**Goal**: theopenlane/core deployed locally + Celestia space-Framework definitions loaded.

- [ ] Local dev environment: docker-compose with theopenlane/core + Postgres 17 + Apache AGE + pgvector
- [ ] Load custom Frameworks (`layers/L1-substrate/frameworks/eu-space-act/`, `iso-24113/`, `itu/`)
  - Hand-author the Framework YAML/JSON files using EU Space Act Articles 1–N, ISO 24113 §§, ITU RR Articles 9, 11, 21, 22
  - Each Control links to evidence types (TLE record, SNL filing, disposal telemetry, etc.)
- [ ] OpenFGA model for the 4-role tetrad (operator, insurer, regulator, admin)
- [ ] SSO/OIDC configuration with EU IdP (Authentik or Keycloak self-hosted)
- [ ] FastAPI orchestration layer scaffold (`app/api/`) — proxies to theopenlane GraphQL
- [ ] Smoke test: end-to-end create-Organization → upload-Evidence → see Evidence linked to Framework Control

**Tools invoked**: `fastapi-expert`, `postgres-pro`, `kubernetes-specialist`, `/investigate` (root-cause for Go service ops issues), `/cso` (auth review).

**Definition of done**: a regulator can log into a stubbed Next.js portal, see an Organization's evidence list, and download a single Evidence record's audit history.

## Phase 2 — L3 SDER engine (weeks 5–8)

**Goal**: Orekit microservice + ITU SNL ingestion + initial risk score generation.

- [ ] Orekit JVM container: Java 21, Spring Boot, gRPC API
  - Endpoints: `propagate(tle, time)`, `conjunction(tle1, tle2, window)`, `frame_convert(state, from, to)`
- [ ] Python client library for the FastAPI side
- [ ] OSTk integration for exploratory notebooks (`ostk-explore/`)
- [ ] Port ITU-Compliance-Assessment-Monitor (`itu-compliance/`):
  - `snl_client.py` — SNL fetch + parse
  - `compliance.py` — proximity check (extended beyond GEO)
  - `filing_maturity.py` — state machine
- [ ] Risk-scoring v0 (`risk-scoring/`) — methodology document + a single-satellite scoring path
- [ ] L2 graph wiring: write conjunction events as Evidence linked to ISO 24113 / EU Space Act obligations

**Tools invoked**: `postgres-pro`, `kubernetes-specialist` (JVM container ops), `/investigate` for any orbital-math regressions, `/codex` for second opinion on risk-scoring methodology (NOT on trust-marked files).

**Definition of done**: an operator's satellite TLE → Orekit propagation → ITU proximity check → conjunction events appear in L2 as Evidence; a stubbed risk score appears on the operator portal.

## Phase 3 — L2 KG + L4 retrieval/drafting (weeks 9–12)

**Goal**: regulatory KG populated, citation-grounded drafting working on at least one obligation type.

- [ ] Annotation tooling: Doccano deployed on Hetzner
- [ ] SpaceRegObligation corpus seed (200–500 annotated provisions across EU Space Act + ISO 24113)
- [ ] Train LEGAL-BERT adapters: NER, deontic modality, cross-ref
- [ ] Ingest pipeline: regulation PDF → parser → extractor → AGE + pgvector
- [ ] L4 retrieval implementation (dual-level pattern from LightRAG over AGE + pgvector)
- [ ] L4 provenance (Context Cores) — Postgres tables + AGE edges
- [ ] L4 drafting agent v0: given an obligation, retrieve evidence, draft a one-paragraph compliance assertion with citations

**Tools invoked**: `rag-architect`, `prompt-engineer`, `database-optimizer`, `claude-api` skill, `/cso` on trust-layer code, `/investigate` for retrieval quality regressions.

**Definition of done**: given an obligation Q from L2, the drafting agent returns a compliance paragraph with citations to ≥2 L2 obligations + ≥1 L1 evidence record. Every claim has a Context Core.

## Phase 4 — L5 dashboards + cross-cutting (weeks 13–16)

**Goal**: working operator dashboard + insurer/regulator portal + production deployment.

- [ ] openmct host scaffold (`layers/L5-dashboard/openmct-host/`)
- [ ] Celestia openmct plugins:
  - Compliance status panel (per Framework, per Control)
  - Evidence-submission widget
  - ITU filing-maturity tracker
  - Conjunction alarm strip
- [ ] Next.js 14 portal app (`apps/portal/` future):
  - Insurer: portfolio risk view, per-asset drill-down, export to CSV
  - Regulator: organization browser, evidence audit view, signed-PDF download
- [ ] OpenFGA enforcement at FastAPI boundary
- [ ] Trust layer: Ed25519 keypair per Organization, Merkle audit chain, PAdES PDF signer
- [ ] Hetzner deployment via Coolify: docker-compose → Coolify deploy → nginx ingress + LetsEncrypt
- [ ] External security review hand-off prep: trust-layer code separated and labeled `MARKED-FOR-EXTERNAL-REVIEW`

**Tools invoked**: `nextjs-developer`, openmct plugin docs (via context7 MCP), `/design-review` for visual QA, `/qa` for end-to-end test, `/cso` final pass.

**Definition of done**: an operator can log in, upload a TLE, see a Risk Score, view ITU-filing maturity, and download a PAdES-signed compliance bundle for handoff to a regulator. A regulator can log in to the portal and audit the same Organization's evidence with traceable provenance.

## Phase 5 — External security review + paid audit (weeks 17–20)

Not in v0.2 build scope; documented for continuity with v0.1. Trust layer goes to Trail of Bits / Quarkslab / Cure53. Budget: €12k–€18k. No code changes in this phase except in response to audit findings.

## Tooling cadence across all phases

- **Daily**: `/context-restore` at session start, `/context-save` + `/retro` at session end.
- **Per PR**: `/review`, `/cso` if touching auth/ingest/rag/trust/rls/bundle.
- **Per layer milestone**: `/plan-eng-review` before starting + `/document-release` after shipping.
- **Weekly**: `/health` for code quality dashboard, `/sync-gbrain` to refresh agent search guidance.
- **Monthly**: `/cso` comprehensive audit; `/retro` rolling up the month.

## Risk register

| Risk | Mitigation |
|---|---|
| theopenlane upstream changes schema incompatibly | Pinned SHA + ADR-0010 (future) for migration path |
| Orekit JVM ops cost overwhelms solo bandwidth | Keep service stateless; budget 5% of weekly time for ops; consider hosted Java PaaS if it bites |
| openmct + Next.js dual-frontend doubles design-system work | Tailwind tokens shared; build one component library that produces both Vue 3 + React variants if needed |
| SpaceRegObligation annotation drags Phase 3 | Start with 100 high-value provisions, expand later; consider contracted annotators |
| LEGAL-BERT space-transfer underperforms | Fall back to GPT-4-class LLM extractor + human-in-loop until corpus matures |
| EU-jurisdiction LLM endpoint latency or quality lower than US peers | Document the trade-off; offer hybrid mode (sensitive data EU only, public-corpus retrieval US-allowed) |

## What is explicitly NOT in v0.2

- Mobile apps
- Real-time conjunction notification SMS/push
- Public regulator-facing API (regulators consume via signed PDFs in v0.2)
- LEO mega-constellation specific tooling beyond ITU/standard frameworks
- Multi-region active-active deployment (single-region Hetzner DE for v0.2)

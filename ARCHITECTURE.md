# ComplianceOS v0.2 — Architecture

## The regulatory path planner (ADR-0018)

The product surface today is the planner. A mission profile goes through four deterministic stages:

1. rules over the open knowledge pack (`knowledge/`) decide which licences apply and why;
2. a scheduler over the prerequisite DAG works out the dates, slack and critical path;
3. the roadmap is assembled;
4. the brief, tracker, deadlines (ICS) and signed dossier are built from it.

```
knowledge/*.yaml ─► app/app/planner/knowledge.py (strict schema + cross-reference validator)
mission profile  ─► rules.py ─► schedule.py ─► plan.py (Roadmap) ─► brief.py / exports.py / tracker.py
                                                      ▲
                     LLM (optional) ─► l4/citations.py (text-level citation check) ─┘
API: app/app/api/planner.py (local mode: loopback-only, no login · team mode: theopenlane + OpenFGA)
Store: app/app/planner/store.py (Postgres planner_* tables; in-memory fallback)
Web: web/ (Next.js 14) · one-command run: compose.yaml
```

The rest of this document describes the platform layers the planner sits on. L3 (orbital mechanics)
and L5 (the openmct dashboard) are parked per ADR-0017.


## One-page summary

ComplianceOS is a 5-layer + cross-cutting system. v0.2 stands on three Apache-2.0 substrates (theopenlane/core, Orekit, openmct) and adopts patterns (not runtimes) from LightRAG, trustgraph, and ComplianceNLP. Production state is single-substrate (Postgres 17 + Apache AGE + pgvector) for EU sovereignty and Merkle-audit simplicity.

```
+---------------------------------------------------------------------+
|                          L5  Dashboards                             |
|  openmct (Vue 3, operator UI)   |   Next.js 14 (insurer + regulator)|
+----------------------|----------+---------------|------------------+
                       |                          |
                       +----------+---------------+
                                  |
                          OpenFGA + Session cookie
                                  |
+---------------------------------v---------------------------------+
|              L4  Drafting Agent  (FastAPI + Python 3.12)         |
|  Retrieval (LightRAG pattern)  |  Extraction (ComplianceNLP arch)|
|  Provenance (Context Cores)    |  Drafting (citation-forced RAG) |
+----------------|------------------------|----------------|------+
                 |                        |                |
                 |                        |                |
+----------------v----+    +--------------v---+    +-------v----+
|   L1 Substrate      |    |  L2 Knowledge    |    |  L3 SDER   |
|   theopenlane/core  |    |    Graph         |    |   Engine   |
|   (Go, GraphQL)     |    |  Postgres + AGE  |    |  Orekit    |
|   Evidence vault    |    |  + pgvector      |    |  (Java)    |
|   Audit log         |    |  EU Space Act    |    |  OSTk      |
|   OpenFGA           |    |  ISO 24113       |    |  (Python)  |
|   SSO/OIDC          |    |  ITU Radio Regs  |    |  ITU SNL   |
|   Frameworks        |    |  RASE labels     |    |  port      |
+----------|----------+    +---------|--------+    +------------+
           |                         |                  ^
           +-----------+-------------+                  |
                       |                                |
                +------v-----------+               +----v-----+
                |  Postgres 17     |               |  Risk    |
                |  (Hetzner DE)    |               |  scoring |
                |  RLS multi-tenant|               |  (Cel.)  |
                +------------------+               +----------+

Cross-cutting:
- Auth: OpenFGA roles (operator | insurer | regulator | admin) shared across L1/L4/L5
- Observability: Prometheus + Grafana + Loki, EU-hosted
- Deploy: Hetzner (DE) via Coolify; nginx ingress; Postgres managed
- Trust layer: Ed25519 signing + Merkle audit chain + PAdES PDF bundles
```

## Layer specifications

### L1 — Substrate (theopenlane/core)

**Role**: foundational entities (Organizations, Users, Frameworks, Controls, Evidence, Procedures, Policies, Questionnaires), authorization (OpenFGA), authentication (SSO/OIDC/Passkeys), audit log (auto-generated entity-history tables), GraphQL API.

**Mode**: vendored at SHA `a76ccb5c35955ed8cb364a7aab65cec9808b854a`. Run as a Go service in its own container. Celestia extensions live as Openlane Frameworks/Controls — defined as YAML/JSON, loaded at startup, NOT as Go source patches.

**Extensions for Celestia**:
- Custom Frameworks: EU Space Act, ISO 24113, ITU Radio Regulations.
- Custom evidence types: TLE record, ITU SNL filing, conjunction report, propagation snapshot, disposal-maneuver telemetry.
- Custom OpenFGA model for 4-role tetrad (operator, insurer, regulator, admin).

**Interfaces**:
- GraphQL (internal cluster network only).
- Webhook subscribers for evidence-uploaded, audit-event, framework-updated.

### L2 — Knowledge Graph (Postgres + AGE + pgvector)

**Role**: machine-actionable representation of regulatory obligations + their cross-references + their applicability rules + their evidentiary requirements.

**Storage**: Postgres 17 with Apache AGE (graph extension) and pgvector (vector extension). Single multi-tenant database with RLS partitioning by Organization.

**Schema** (conceptual; full schema in `layers/L2-knowledge-graph/SCHEMA.md` future):
- Nodes: `Regulation`, `Article`, `Provision`, `Obligation`, `Entity` (operator, satellite, mission, ground station, etc.), `Term`, `OrbitalSlot`, `Filing`.
- Edges: `cites`, `applies_to`, `requires_evidence`, `references`, `superseded_by`, `derived_from`, `has_filing_state`.
- Embeddings: per-chunk and per-obligation, model BAAI/bge-m3 (EU-hostable).
- RASE labels: per-obligation Requirement/Applicability/Selection/Exception slots (see ADR-0008).

**Extractor** (`layers/L2-knowledge-graph/extractors/`):
- Pipeline based on ComplianceNLP architecture (ADR-0006): LEGAL-BERT encoder + three joint heads (NER, deontic modality, cross-ref).
- Adapter-tuned on SpaceRegObligation corpus (`layers/L2-knowledge-graph/corpus/`).

**Ingest**: regulatory documents → parser → extractor → AGE graph + pgvector chunks → review queue (human-in-loop until F1 > 0.85).

### L3 — SDER Engine (Space Debris / Environmental Risk)

**Role**: defensible orbital math powering insurer risk scoring and regulator-facing compliance assertions.

**Components**:
- **Orekit microservice** (`orekit-service/`) — Java 21, Spring Boot. Wraps Orekit (ADR-0002). Exposes gRPC. Stateless. Runs in its own container.
- **OSTk Python layer** (`ostk-explore/`) — for research notebooks, prototyping, internal R&D. Numbers exposed to operators/insurers/regulators come from Orekit, not OSTk.
- **ITU compliance** (`itu-compliance/`) — port of ITU-Compliance-Assessment-Monitor (ADR-0009). Extended beyond GEO to LEO/MEO/HEO.
- **Risk scoring** (`risk-scoring/`) — Celestia-original. Combines conjunction probability, filing-maturity status, disposal compliance, and operator track record into an insurer-priced risk score. Methodology documented and citable.

**Data flow**: external TLE feeds (CelesTrak, Space-Track) → Orekit propagation → conjunction events + SNL proximity checks → events written to L2 KG as evidence → risk-scoring aggregates.

### L4 — Drafting Agent

**Role**: produce regulator-defensible compliance drafts, gap analyses, and audit responses. Every output cites specific L2 obligations + L1 evidence + L3 numbers. No hallucinations.

**Components**:
- **Retrieval** (`retrieval/`) — LightRAG dual-level pattern (ADR-0004) over Postgres pgvector + AGE Cypher. Reranker: BAAI/bge-reranker-v2-m3 (EU-hosted inference).
- **Extraction** (`extraction/`) — ComplianceNLP three-head pipeline (NER, modality, cross-ref) — shares the L2 extractor codebase.
- **Provenance** (`provenance/`) — Context Core schema (ADR-0005). Every drafted claim has a source manifest: regulation provision, evidence record(s), derivation method, timestamp.
- **Drafting** (`drafting/`) — prompt templates + tool-using agent. LLM calls go to EU-jurisdiction endpoints (Anthropic EU, Mistral, or self-hosted). Output is PAdES-signed PDF for regulator delivery.

**Trust boundary**: drafting code lives in `app/api/trust/draft/**` (future). Files marked `# MARKED-FOR-EXTERNAL-REVIEW` per v0.1 sovereignty rules.

### L5 — Dashboards

**Role**: stakeholder UI.

- **Operator dashboard**: openmct host (Vue 3, plugin-first). Celestia plugins for compliance status, evidence submission, ITU filing-maturity tracker, conjunction alarms. ADR-0003.
- **Insurer + regulator portal**: Next.js 14 App Router app (future `apps/portal/`). shadcn/ui + Tailwind. Portfolio risk views (insurer), evidence/audit views (regulator).
- **Shared auth**: same OpenFGA session crosses both frontends.

### Cross-cutting

- **Auth**: OpenFGA model with 4 roles (operator, insurer, regulator, admin). Backed by theopenlane/core's auth surface.
- **Multi-tenancy**: Postgres RLS by Organization. Reinforced by OpenFGA relationship checks at the API boundary.
- **Trust layer**: Ed25519 keypair per Organization. Merkle audit chain (per v0.1 design) covering every L1 evidence event. PAdES PDF bundles for regulator handoff.
- **Observability**: Prometheus (metrics), Grafana (dashboards), Loki (logs). All EU-hosted.
- **Deploy**: Hetzner DE infrastructure via Coolify. Postgres managed (EU-resident). No US-hosted services for application data.

## Data flow examples

### "Did this operator comply with ISO 24113 disposal requirements for Sat XYZ?"

1. L5 (regulator portal) calls L1 GraphQL `evidence(orgId, satelliteId, obligationRef="ISO-24113-§6.2")`.
2. L1 returns Evidence records linked to that obligation.
3. L4 drafting agent kicks off:
   - L4 retrieval: pgvector ANN on the obligation text + AGE traversal from Obligation node outward.
   - L4 extraction: confirms each retrieved Evidence cites the right Article via cross-ref head.
   - L3 risk scoring: pulls disposal-maneuver telemetry and computes residual-debris probability.
   - L4 provenance: builds a Context Core for each claim (regulation → evidence record(s) → propagation snapshot).
4. L4 drafting renders the compliance assertion as a PAdES-signed PDF, citing all sources.
5. L5 regulator portal serves the PDF + a graph-traversal view linking to underlying Evidence in L1.

### "Is operator ACME compliant with their ITU filing for slot 21.5°E?"

1. L3 ITU module fetches latest SNL.
2. Cross-references ACME's recorded satellite longitude against the SNL allocation for 21.5°E within 1.0° proximity.
3. Filing-maturity state machine determines whether the filing is in early-stage / late-stage / brought-into-use / suspended.
4. Result written to L2 KG as an evidence chain attached to the relevant ITU obligation.
5. L4 produces a status snapshot citing the SNL fetch timestamp and the proximity calculation.

## Where each adopted resource fits

| Resource | Layer | Adoption mode | ADR |
|---|---|---|---|
| theopenlane/core | L1 | Substrate (Go service) | 0001 |
| Orekit | L3 | Substrate (JVM service) | 0002 |
| OSTk | L3 | Python lib (exploration) | 0002 |
| openmct | L5 | Plugin host (Vue) | 0003 |
| LightRAG | L4 | Pattern (re-implemented) | 0004 |
| trustgraph | L4 | Pattern (Context Cores) | 0005 |
| ComplianceNLP paper | L2 + L4 | Architecture (re-implemented) | 0006 |
| Postgres + AGE + pgvector | L1/L2/L4 state | Production substrate | 0007 |
| accord-nlp | L2 | RASE annotation schema | 0008 |
| ITU-Compliance-Assessment-Monitor | L3 | Port (SNL + maturity) | 0009 |

## gbrain integration

gbrain is the Claude agent's knowledge graph (PGLite-backed). It mirrors this architecture so future agent sessions can navigate it. It is **not production infrastructure** (ADR-0007).

Pages created during scaffolding:
- `complianceos-overview`
- `layer-l1-substrate`, `layer-l2-knowledge-graph`, `layer-l3-sder-engine`, `layer-l4-drafting-agent`, `layer-l5-dashboards`, `layer-cross-cutting`
- `adr-0001` through `adr-0009`

Links established (see `ingest-to-gbrain.sh`):
- Each layer page links to its governing ADRs.
- Each ADR page links to the layers it affects.
- Vendor pages (one per dep) link to the layer they serve.

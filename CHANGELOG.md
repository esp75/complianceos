# Changelog

All notable changes to ComplianceOS are documented here. Format: [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- Knowledge-pack QA (`python -m app.planner.pack_qa`): offline checks (https URLs, no future dates)
  and a live check that each quoted excerpt is still on the page it cites (`found`, `partial`,
  `not_found`, `unreadable`, `blocked`, `unsupported`, `unreachable`). It runs weekly with the link
  check and fails only on `not_found`.
- Standalone offline verifier (`verifier/complianceos_verify.py`) for signed dossiers and history.
- Branded dossier PDF: cover page, running header, reviewer sign-off block.
- `watch` service in `compose.yaml` runs the Watch daily.

### Security
- Postgres row-level security on the planner's workspace tables (missions, applications, events,
  contacts, history checkpoints, usage, alert recipients). Each call runs in a transaction that names
  its workspace; with none set, nothing is visible. When the API connects as a superuser it switches
  to a `NOLOGIN` role, `complianceos_planner`, so the policies apply. The alert job lists workspaces
  from a new id-only `planner_workspace` table.
- `POST /missions/{id}/brief?ai=true` needs write access and is limited to six Claude calls per
  workspace per minute (a `/cso` finding: any viewer could spend the deployment's LLM budget).
- `/bundle/sign` (THREAT_MODEL findings 1–3): appends to the bundle chain under a per-org lock with
  unique indexes that keep the chain linear; signing requires `can_edit` on the organization (it
  was `can_view`); a framework filter is recorded in the signed manifest (`trust-bundle/v1`,
  `scope`) and on the PDF.
- HttpFetcher checks every redirect hop and the connected peer address for non-public targets and
  fails closed on DNS errors; each hop connects to the address it checked (SNI and Host kept), which
  closes the DNS-rebinding window. SMTP refuses cleartext credentials.
- Application owners: `PATCH /applications/{id}` takes `owner`; `GET /program` adds a per-owner
  workload (open, overdue, markets). The Workspace page shows an Owners table and a cross-mission
  Source changes list.
- The Watch v0 (ADR-0019): checks every source the knowledge pack cites, records changes and
  unreachable or non-HTML sources, and links each change to the workspace's tracked applications.
  API: `GET /watch/changes`, `GET /missions/{id}/watch`, `POST /watch/run`. CLI:
  `python -m app.planner.watch run|changes`. Web: a Watch tab on each mission.
- Watch alerts and sources (ADR-0020): `run --alert` emails a digest of changes that touch tracked
  applications over a configurable SMTP relay; PDF sources are read; the pack can list official
  RSS/Atom `feeds` (GB and US ship) that report new matching publications; changed pages get an
  advisory Claude triage label when an Anthropic key is set.

- Signed program history and pilot usage (ADR-0021): `POST /history/export` returns an Ed25519-signed
  Merkle export of application events that names the previous export's root;
  `GET /missions/{id}/history`; `POST /usage` and `GET /usage/summary` count feature use.

- Dossier (ADR-0022): "Likely friction points" and "Who decides" sections, both citation-enforced;
  a basis label (statute, practice, estimate, derived) on risk and path paragraphs; a Markdown
  reviewer package with a per-licence checklist (`GET /missions/{id}/dossier.md`).
- Signed dossier: the Ed25519 signature now covers the roadmap **and** the brief (friction points,
  decision makers, basis labels), not the roadmap alone. `GET /missions/{id}/dossier.signed.json`
  serves the signed data; the Markdown package ends with the SHA-256 and signature. The PDF's
  attachment is now `dossier-signed.json` (format `complianceos-dossier/1`).
- Per-workspace Watch alert recipients (`GET`/`PUT /alerts/recipients`) and a Workspace page with
  the recipients editor and the pilot usage report. The deployment-wide list is the fallback.

- Austria joins the knowledge pack (draft): the space activity approval under the Weltraumgesetz
  and Weltraumverordnung, read from the RIS open-data API, with the BMIMI Weltraumbehörde as the
  authority. Germany: see below.
- Germany joins the knowledge pack (draft): the ground-station frequency assignment (TKG §§ 91, 92)
  and the ITU satellite filing with the Bundesnetzagentur (TKG § 95), quoted verbatim from the
  official gesetze-im-internet.de text. Space-activity authorisation is not covered.
- Czech Republic joins the knowledge pack (draft): the individual right to use radio frequencies for a
  ground station (Act 127/2005 § 17(1)), granted by the ČTÚ. Text checked against a consolidation, not e-Sbírka.
- Spain joins the knowledge pack (draft): the title for using the radio public domain for a ground station
  (Ley 11/2022 art. 88(3), with its six-week rule and coordination exception), and the State reservation of
  orbit-spectrum use for communications satellites (art. 85(5)).
- Denmark joins the knowledge pack (draft): the radio frequency permit for a ground station (Lov om
  radiofrekvenser § 6(1)), issued by Digitaliseringsstyrelsen.
- Norway joins the knowledge pack (draft): the frequency permit for a ground station (ekomloven § 11-2)
  and the satellite system filing to the ITU register on application (§ 11-16), both delegated to Nkom.
- Canada: the space station spectrum licence and ITU filing through ISED (CPC-2-6-02 issue 7, ss. 1, 3, 5.2,
  10), with the 126-day service standard and the six-month link between filing and application.
- Germany: the Watch follows the Bundesgesetzblatt Teil I feed (recht.bund.de) for new telecoms,
  frequency, satellite and space instruments.
- Canada joins the knowledge pack (draft): the radio authorisation for a ground station (Radiocommunication
  Act ss. 4(1), 5(1)), issued by the Minister of Industry through ISED. The ITU filing route is not covered.
- Ireland joins the knowledge pack (draft): the wireless telegraphy licence for a ground station
  (Wireless Telegraphy Act 1926, revised), granted by ComReg. The ITU filing route is not covered.
- Netherlands joins the knowledge pack (draft): the frequency licence for a ground station under the
  Telecommunicatiewet (art. 3.13(1)), issued through the RDI. The ITU filing route is not covered.
- Austria's ITU route checked against TKG 2021 and the Weltraumverordnung: no Austrian filing
  administration is named. The operator's ITU coordination documents (WRV § 2(6)) are now cited in the
  space approval record.

- One client, many markets: `GET /program` folds every mission in a workspace into one row per
  jurisdiction (licences needed, tracked, in progress, granted, overdue, next date), shown as the
  Markets table on the Workspace page.

### Changed
- Environment variables use the `COMPLIANCEOS_` prefix (was `CELESTIA_`). The old names still work for
  now: each fills its unset `COMPLIANCEOS_` twin at startup, with one warning naming them.
- `POST /watch/run` allows one run at a time (409) and one per minute per process (429).
- `verify_history` checks the fingerprint matches the embedded key and accepts a
  `trusted_fingerprint` to pin the signer; the embedded key alone proves integrity, not origin.

## [0.2.0] — 2026-05-15 — "Stand on Giants"

Strategic shift from "build everything" (v0.1) to "fork three Apache-2.0 substrates and add the space-specific layer on top."

### Added
- 9 vendored upstream dependencies under `external/` with pinned SHAs (theopenlane/core, Orekit, OSTk, openmct, LightRAG, trustgraph, ComplianceNLP, accord-nlp, ITU-Compliance-Assessment-Monitor)
- 8 cherry-picked Jeffallan claude-skills under `.claude/skills/` (RAG Architect, Prompt Engineer, Postgres Pro, Database Optimizer, MCP Developer, FastAPI Expert, Next.js Developer, Kubernetes Specialist)
- 9 Architecture Decision Records (`adr/0001` through `adr/0009`)
- Layer-scoped sub-projects: `layers/L1-substrate/`, `L2-knowledge-graph/`, `L3-sder-engine/`, `L4-drafting-agent/`, `L5-dashboard/`, `cross-cutting/`
- gbrain-ingested architecture pages (Overview, L1–L5, each ADR)
- License matrix and dependency map under `docs/`

### Changed
- L1 build path: "build evidence vault + audit log + RBAC + SSO" → "fork theopenlane/core, model space frameworks as Openlane Frameworks"
- L3 orbital math path: "build custom propagation" → "Orekit JVM microservice (ESA/CNES governance) for defensible numbers, OSTk Python for exploration"
- L5 dashboard direction: "Next.js custom dashboard" → "openmct (NASA Ames) plugin host for operator views; Next.js retained for insurer/regulator portals" (see ADR-0003)
- L2 KG store: gbrain MCP retained as **agent memory only**; production KG remains Postgres 17 + Apache AGE + pgvector per v0.1's EU sovereignty rules (see ADR-0007)
- L4 retrieval: re-implement LightRAG's dual-level retrieval pattern over Postgres+AGE+pgvector (NOT vendor LightRAG storage)

### Removed
- trustgraph as a runtime (Cassandra+Pulsar+Qdrant incompatible with EU-sovereign Postgres-only constraint) — pattern adoption only (Context Cores provenance schema)

### Decisions locked 2026-05-15
- ADR-0010: MVP LLM policy = Claude only (Anthropic EU endpoint). Mistral deferred post-MVP.
- ADR-0011: External security review vendor = Quarkslab (FR) primary, Cure53 (DE) backup. Trail of Bits dropped.

### Carried over from v0.1
- EU-sovereign infrastructure rules (Hetzner, no US-hosted prod data)
- Trust-layer external-review convention (`MARKED-FOR-EXTERNAL-REVIEW` header)
- Postgres 17 + Apache AGE + pgvector + FastAPI + Next.js 14 stack
- Ed25519 signing + Merkle audit chain + signed PAdES bundles

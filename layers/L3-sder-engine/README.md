# L3 — SDER Engine (Space Debris / Environmental Risk)

Defensible orbital math powering insurer scoring and regulator-facing compliance. See ADRs [0002](../../adr/0002-orekit-jvm-microservice-for-l3.md), [0009](../../adr/0009-port-itu-compliance-monitor-snl-and-filing-maturity.md).

## Role

- Propagate satellite states (TLE → state vectors at arbitrary epochs).
- Detect conjunctions (close-approach events between any two cataloged objects).
- Cross-reference satellite positions against ITU SNL allocations.
- Track ITU filing-maturity state through its lifecycle.
- Compute Celestia's insurer-priced risk score.

## Architecture summary

- **Orekit microservice** (`orekit-service/`) — Java 21, Spring Boot, gRPC API. Wraps Orekit. Stateless. Authoritative for any number consumed by insurers/regulators.
- **OSTk** (`ostk-explore/`) — Python bindings to Open Space Toolkit. For internal R&D, notebooks, prototyping. Never the source of stakeholder-facing numbers.
- **ITU compliance** (`itu-compliance/`) — port of ITU-Compliance-Assessment-Monitor (SNL parser + proximity check + filing-maturity state machine). Extended beyond GEO to LEO/MEO/HEO.
- **Risk scoring** (`risk-scoring/`) — Celestia-original methodology. Combines conjunction probability + filing-maturity state + disposal compliance + operator track record into an insurer-priced score.

## Sub-folders

- `orekit-service/` — Java 21 Spring Boot service. gRPC API. Stateless. Containerized.
- `ostk-explore/` — Python research surface. Notebooks. Not production-pathed.
- `itu-compliance/` — SNL client + proximity + filing-maturity state machine (Python).
- `risk-scoring/` — Celestia-original. Methodology doc + Python module.

## Phase 2 deliverables (see ROADMAP.md)

First slice complete (REST/JSON, ADR-0013). See the [engineering log](../../docs/explanation/engineering-log.md) for the M0–M7 log.

- [x] Orekit service: `propagate`, `conjunction`, `frame_convert` endpoints (REST/JSON)
- [x] Python client library for FastAPI-side consumers (`app/app/clients/orekit.py`)
- [ ] OSTk integrated for `ostk-explore/` notebooks — deferred (research surface)
- [x] Port `snl_client.py`, `compliance.py`, `filing_maturity.py` from upstream (GEO)
- [ ] LEO/MEO/HEO extensions to proximity check — deferred (no authoritative source yet; stubbed)
- [x] Risk-scoring v0: methodology doc + single-satellite scoring path
- [x] Conjunction events written to L1 as `conjunction_report` Evidence (ADR-0012), risk on portal

## Skills to invoke

- `kubernetes-specialist` — for Orekit service ops (JVM container shape)
- `postgres-pro` — for L2 KG writes (conjunction events → Evidence)
- `/investigate` — for any orbital-math regressions (Iron Law: no fix without root cause)
- `/codex` — second opinion on risk-scoring methodology (NOT on trust-marked files)

## Upstream reference

- Orekit: `external/orekit/` at SHA `fb3a845cd8ef453413bda2a6ad41d281a8b9a760`
- OSTk: `external/ostk/` at SHA `1eaf348fbcd9bc9265aaa47398dfe0ef51709fda`
- ITU-Compliance-Assessment-Monitor: `external/itu-compliance-monitor/` at SHA `d8bf1b441f49265482b5b48d6131123d68574f11`

## Open questions

- ~~gRPC vs REST for the Orekit service interface.~~ **Resolved (ADR-0013): REST/JSON for v0; gRPC
  deferred behind a Phase-3 benchmark.**
- LEO mega-constellation filing data source — ITU SNL is GEO-centric; investigate operator-specific feeds (Space-Track, EUSST).
- Risk-scoring methodology peer review path — consider engaging an aerospace insurance broker for a non-trivial review before insurer pitches.

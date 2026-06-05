# ADR 0009 — Port ITU-Compliance-Assessment-Monitor SNL parser + filing-maturity state machine to L3

**Status**: Accepted — 2026-05-15
**Decision-makers**: Maxime Kadr (solo)

## Context

ITU (International Telecommunication Union) maintains the Space Network List (SNL) — the authoritative registry of orbital slot and frequency allocations. Operators must demonstrate compliance with their ITU filings, and filings progress through a defined state machine: **early-stage → late-stage → brought-into-use → suspension** (where applicable).

**ThomasGRoberts/ITU-Compliance-Assessment-Monitor** (MIT, Python) is the only satellite-specific compliance monitor in the candidate set. It downloads the SNL, cross-references live satellite longitude against ITU allocations, and tracks filing maturity. GEO-only. Last update April 2025 (~13 months stale).

The repo's code is small, MIT-licensed, and the SNL parser + maturity state machine are reusable IP.

## Decision

Port the SNL ingestion and filing-maturity components into Celestia L3. Do not vendor the repo as a runtime.

- Source repo at SHA `d8bf1b441f49265482b5b48d6131123d68574f11` (in `external/itu-compliance-monitor/`) for reference.
- Port target: `layers/L3-sder-engine/itu-compliance/`.
  - `snl_client.py` — ports `Code/snl.py` (SNL fetch and parse).
  - `compliance.py` — ports `compliance_daily.py` and `compliance_historical.py`, expanded beyond GEO to LEO/MEO/HEO (Celestia-original work).
  - `filing_maturity.py` — implements the state machine vocabulary (early-stage / late-stage / brought-into-use / suspended). Provides typed Python enums and Postgres ENUM equivalents.
- Modeled into the L2 KG as obligations linked to filings; filings carry maturity state as a property edge.

## Consequences

**Positive**
- Saves ~2–4 weeks vs cold-starting an SNL ingestion + maturity model.
- MIT license is permissive; no contamination risk.
- Citable as prior art if a regulator or insurer asks where the maturity vocabulary comes from.

**Negative**
- Upstream is stale; bug fixes are Celestia-owned.
- GEO-only original scope — Celestia must implement LEO/MEO/HEO logic from scratch (which we'd have to do regardless).
- Single-author thesis-adjacent code; defensive review required before integration.

**EU sovereignty check**
- SNL is fetched from itu.int (international/Geneva). ✓ compatible.
- No US-hosted services involved.

## Alternatives considered

- **Cold-start SNL parser** — reinvents wheel; rejected.
- **Adopt upstream as a runtime dependency** — stale + unmaintained risk; rejected.
- **Use a commercial SSA provider for ITU compliance** — black-box, expensive, unverifiable. Rejected.

## Open questions

- LEO/MEO/HEO compliance logic — what authoritative source exists? ITU SNL is GEO-centric; LEO mega-constellations file via different mechanisms. Investigate in Phase 2.
- Whether to upstream Celestia's LEO extensions back to ThomasGRoberts/ITU-Compliance-Assessment-Monitor. Default: yes, after Phase 2.

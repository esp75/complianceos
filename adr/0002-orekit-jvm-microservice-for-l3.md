# ADR 0002 — Orekit as a JVM microservice for L3 defensible orbital math

**Status**: Accepted — 2026-05-15
**Decision-makers**: Maxime Kadr (solo)

## Context

L3 (SDER engine) outputs orbital-mechanics numbers (propagation, conjunction probabilities, ITU-slot proximity, debris risk, insurer scoring inputs). Two stakeholder groups consume these numbers and demand defensibility:

- **Insurers**: require traceability to peer-reviewed propagation/conjunction methodology before they will price coverage.
- **Regulators**: require methodology that an auditor can validate against ESA or CNES baselines.

Celestia cannot ship hobbyist propagators here.

Three candidates were assessed:

- **CS-SI/Orekit** (Java) — Apache-2.0, maintained since 2002 by CS GROUP, PMC includes ESA, CNES (operational user), U.S. Naval Research Lab, Airbus Defence and Space, Thales Alenia Space, Swedish Space Corporation. CII-certified. v13.1.5 (2026-05-03).
- **open-space-collective/open-space-toolkit (OSTk)** (C++/Python) — Apache-2.0, modular, community-collective maintained, 203 stars, no marquee institutional backing visible.
- **NRA-Research/poliastro2** (Python) — early-stage fork, "no production release yet."

Orekit has the strongest provenance for insurer/regulator defensibility. It is also Java, which conflicts with Celestia's Python/TypeScript stack.

## Decision

Adopt **Orekit as a JVM microservice** at SHA `fb3a845cd8ef453413bda2a6ad41d281a8b9a760`.

- Service lives in `layers/L3-sder-engine/orekit-service/`.
- Java 21, Spring Boot wrapper exposing a thin gRPC (preferred) or REST API.
- Python (FastAPI) calls Orekit over the cluster-internal network only. Never link Java into the FastAPI process; never embed JCC/JPype.
- Adopt **OSTk in parallel** for Python-native exploratory work (notebooks, prototypes, internal R&D). Numbers exported to operators/insurers/regulators come from Orekit.
- Skip **poliastro2** — abandoned-fork stage.

## Consequences

**Positive**
- Defensibility narrative: "Our propagation uses the same library ESA and CNES use operationally." This is the single strongest credibility lever in Celestia's pitch to insurers and regulators.
- Apache-2.0 = clean.
- JVM isolation means Java is firewalled to one container; no Java in the Celestia application code.

**Negative**
- JVM ops cost: container image size, cold-start latency, ops surface (JVM tuning, GC profiling). Mitigated by keeping the service stateless and horizontally scalable.
- Java + Python wire format requires a contract document — see `layers/L3-sder-engine/orekit-service/CONTRACT.md` (future).
- Bus factor on Orekit-python wrapper (orekit-python uses JCC/Hipparchus) is low; we sidestep this by using gRPC, not the wrapper.

**EU sovereignty check**
- CS GROUP (maintainer) is French. ESA, CNES are EU institutions. Provenance aligns with EU narrative.

## Alternatives considered

- **OSTk as primary** — Python-native is operationally simpler but provenance is weaker; reserved for exploration.
- **Build custom propagator in Python** — multiple engineer-months; no insurer defensibility; rejected.
- **Embed Orekit in FastAPI via JPype** — entangles JVM lifecycle with FastAPI process; rejected.

## Open questions

- gRPC vs REST for the Orekit service. Default to gRPC; benchmark in Phase 2.
- Whether to ship a Java-domain skill (e.g., Jeffallan's `java-architect`) into `.claude/skills/`. Default no — confine Java to the service.

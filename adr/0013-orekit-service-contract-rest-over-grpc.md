# ADR 0013 — Orekit service contract: REST/JSON for v0 (gRPC deferred)

**Status**: Accepted — 2026-06-06
**Decision-makers**: Maxime Kadr (solo)
**Related**: [ADR-0002](./0002-orekit-jvm-microservice-for-l3.md) (Orekit as a JVM microservice — resolves its "gRPC vs REST" open question), [ADR-0009](./0009-port-itu-compliance-monitor-snl-and-filing-maturity.md) (ITU port), [ADR-0012](./0012-fastapi-theopenlane-contract.md) (BFF as the only integration boundary)

## Context

ADR-0002 adopted Orekit as a Java 21 / Spring Boot JVM microservice for L3 and left one
open question: **gRPC vs REST** for the FastAPI ↔ Orekit interface, with "default gRPC,
benchmark in Phase 2." Phase 2 is now starting and the interface must be fixed before any
service code is written (CLAUDE.md: "Before modifying anything in `external/`, write an ADR
documenting the divergence and pin the new SHA").

Constraints that shape the decision:

- The Orekit service exposes **three unary request/response operations**: `propagate`,
  `conjunction`, `frame_convert`. No streaming, no high fan-out hot path.
- The Phase-1 BFF already calls every upstream (`openlane`, `openfga`) through a single
  shared `httpx.AsyncClient` stored in `app.state`, with thin typed client wrappers
  (`app/app/clients/*.py`). This is the established pattern (ADR-0012).
- Solo build. Toolchain cost is paid by one person.

## Decision

**1. The Orekit service speaks REST/JSON over HTTP for v0.** Spring Boot Web
(`@RestController`), JSON request/response bodies, a uniform error envelope. The Python side
adds `app/app/clients/orekit.py` — a thin typed wrapper over the **same shared
`httpx.AsyncClient`**, mirroring `clients/openlane.py`. No `.proto`, no codegen, no second
transport in the BFF lifespan.

**2. gRPC is deferred behind a Phase-3 benchmark gate.** All Orekit calls are localized to
`OrekitClient` (Python) and the controller layer (Java), so the transport can be swapped
without touching any router. gRPC is revisited only if Phase-3 load testing shows REST is a
measured bottleneck. This **resolves ADR-0002's open question** for v0: the honest benchmark
for a solo build is that REST ships a working slice in days, while gRPC costs a Java+Python
codegen toolchain (`protobuf-maven-plugin`/`grpc-java` + `grpcio-tools`) kept in lockstep on
every contract change, for no win on three unary endpoints.

**3. The wire contract is fixed and versioned.** The endpoint shapes, units, frames, and
error envelope live in `layers/L3-sder-engine/orekit-service/CONTRACT.md` (the document
ADR-0002 referenced as "(future)"). Summary:

- `POST /propagate` — `{tle:{line1,line2}, epoch}` → `{position[km], velocity[km/s], frame, epoch}`
- `POST /conjunction` — `{tle1, tle2, window:{start,end,stepSeconds}}` →
  `{events:[{epoch, missDistanceKm, relativeSpeedKmS}], minMissDistanceKm}`
- `POST /frame_convert` — `{state, fromFrame, toFrame}` → converted state
- `GET /healthz` (liveness), `GET /readyz` (200 only once orekit-data is loaded)
- Errors: `{ "error": { "code", "message" } }`, HTTP 400 for bad input, 503 when not ready.
- Units: distances km, velocities km/s, times UTC ISO-8601, frames `EME2000` / `ITRF` / `TEME`.

**4. Conjunction v0 = sampled minimum miss distance.** The service propagates both objects
across the window at `stepSeconds` and reports local minima of the inter-object range, plus
the global minimum. It does **not** compute probability-of-collision (Pc) — that requires
covariance data operators rarely supply and is a research surface. Documented as a v0
limitation in `CONTRACT.md` and the risk-scoring methodology so it is never mistaken for an
insurer-grade collision probability.

**5. orekit-data is provided by a mounted volume, not baked into the image.** Orekit cannot
propagate without its data files (EOP, leap seconds, gravity models). A
`scripts/fetch-orekit-data.sh` downloads the canonical `orekit-data` set into a gitignored
directory; docker-compose mounts it read-only at `/orekit-data`. `/readyz` fails until the
`DataContext` confirms the data is loaded, so a missing-data misconfiguration surfaces at
boot, not on first request.

**6. The service depends on a released Orekit, not the vendored SNAPSHOT.** The vendored
source at `external/orekit/` is `14.0-SNAPSHOT` on `develop` (pinned SHA
`fb3a845cd8ef453413bda2a6ad41d281a8b9a760`). A SNAPSHOT is not a reproducible build input, so
the running service depends on the latest **released** Orekit Maven coordinate on the audited
line — **`org.orekit:orekit:13.1.5`** (the release ADR-0002 cites, 2026-05-03), with
Hipparchus pulled transitively. The version↔SHA mapping is recorded here and in
`docs/upstream-watch.md`: audited source line = Orekit 13.x; running jar = `13.1.5`. When the
vendored line advances to a released 14.x, bump the coordinate in a follow-up ADR.

## Consequences

**Positive**
- The `OrekitClient` drops into the Phase-1 pattern verbatim — one shared transport, one
  error-class convention, `curl`-able endpoints for debugging the JVM cold-start.
- Transport is swappable later because the contract is centralized in one client + the
  controller layer.
- Reproducible builds: the running jar is a released, audited Orekit version.

**Negative**
- JSON is less strictly typed than protobuf; the contract is enforced by `CONTRACT.md` +
  pydantic models on the Python side + DTO records on the Java side, not by a shared schema.
- A future gRPC migration, if the benchmark ever justifies it, is real work — bounded because
  the call sites are localized.
- Running a released 13.1.5 while the vendored source tracks 14.0-SNAPSHOT is a deliberate
  version skew; tracked in `docs/upstream-watch.md` and revisited when 14.x releases.

**EU sovereignty check**
- No change to ADR-0002's provenance analysis (Orekit / CS GROUP, FR). REST vs gRPC is a wire
  format, not a data-residency decision. orekit-data is fetched from the Orekit project's
  canonical source and mounted locally. ✓ compatible.

## Alternatives considered

- **gRPC now (ADR-0002's stated default)** — rejected for v0; two codegen toolchains kept in
  lockstep for three unary endpoints, plus a second transport in the BFF lifespan, with no
  measured benefit. Reconsidered behind a Phase-3 benchmark.
- **Bake orekit-data into the image** — rejected; the data updates faster than the code and
  bloats the image; a read-only volume keeps the image lean and the data swappable.
- **Probability-of-collision in v0** — rejected; needs covariance inputs and is a research
  surface. Deferred; v0 ships deterministic min-miss-distance.

## Open questions

- Phase-3 REST-vs-gRPC benchmark — the exit clause for decision 2. Run under realistic
  conjunction-batch load before committing to a migration.
- Exact orekit-data pin/source URL — recorded in `CONTRACT.md`; revisit whether to vendor a
  frozen data snapshot for fully reproducible regulator-facing runs (Phase 4 hardening).

# orekit-service — Celestia L3 orbital-math microservice

Java 21 + Spring Boot wrapping [Orekit](https://www.orekit.org/), exposed over REST/JSON.
The **only** Java in the codebase (CLAUDE.md); the FastAPI BFF calls it over the
`celestia-l1` network via `app/app/clients/orekit.py`. Never embed this in the Python
process (no JPype/JCC) — ADR-0002.

- Decision record: [ADR-0002](../../../adr/0002-orekit-jvm-microservice-for-l3.md) (why Orekit),
  [ADR-0013](../../../adr/0013-orekit-service-contract-rest-over-grpc.md) (why REST for v0).
- Wire contract: [CONTRACT.md](./CONTRACT.md).

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/healthz` | liveness (never touches Orekit) |
| GET | `/readyz` | readiness — 200 only once orekit-data is loaded, else 503 |
| POST | `/propagate` | TLE → state vector at an epoch (M2) |
| POST | `/conjunction` | sampled min-miss-distance screening over a window (M2) |
| POST | `/frame_convert` | convert a state between reference frames (M2) |

## orekit-data (required)

Orekit will not propagate without its data files. They are mounted at runtime, not baked
into the image (ADR-0013). Fetch them once:

```bash
./scripts/fetch-orekit-data.sh
# populates cross-cutting/deploy/orekit-data/ which compose mounts read-only at /orekit-data
```

`/readyz` returns 503 until the data is present and loadable.

## Build & run

```bash
# Unit tests (web layer; no orekit-data needed)
mvn test

# Container (multi-stage; JRE-only runtime)
docker build -t celestia/orekit:dev .
docker run --rm -p 8090:8090 -v "$PWD/orekit-data:/orekit-data:ro" celestia/orekit:dev
curl localhost:8090/healthz   # {"status":"ok"}
curl localhost:8090/readyz    # {"status":"ready"} once data is mounted
```

In the full stack the service is gated behind the compose `sder` profile (see
`cross-cutting/deploy/docker-compose.yml`).

## Version pin

Runs released `org.orekit:orekit:13.1.5`; the vendored source line at `external/orekit/`
is `14.0-SNAPSHOT`. The skew is intentional and tracked in `docs/upstream-watch.md`.

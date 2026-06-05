# Celestia deploy — L1 substrate dev stack

Self-contained docker-compose stack for the Phase 1 L1 substrate. Celestia-owned
(ADR-0012); replicates theopenlane's published-image env contract with pinned tags.

## Services

| Service | Image | Port(s) | Role |
|---|---|---|---|
| `postgres` | postgres:17 | 5432 | theopenlane operational DB (`core`, `jobs`, `openfga`) |
| `openfga` (+`openfga-migrate`) | openfga/openfga:v1.15.1 | 8080/8081/3000 | authorization store + playground |
| `redis` | redis:7.4.9-alpine | 6379 | sessions / cache |
| `core` | ghcr.io/theopenlane/core:v1.20.6 | 17608 | **L1 substrate** — GraphQL `/query`, `/ready`, `/.well-known` |
| `riverboat` | ghcr.io/theopenlane/riverboat | — | River job-queue worker (not on the health path) |
| `dex` | ghcr.io/dexidp/dex:v2.45.1 | 5556 | local OIDC IdP (dev) |
| `app` | celestia/api:dev (built) | 8000 | Celestia FastAPI BFF |

Apache AGE + pgvector (L2 KG) are **not** here — they belong to a separate
`kg-postgres` instance added in M6, never mixed into theopenlane's migration-owned DB.

## Prerequisites

A Docker runtime. Local dev uses **colima** (`colima start`); `docker info` must connect.

## Run

```bash
cd cross-cutting/deploy
docker compose up -d
docker compose ps                 # all services up; openfga + postgres healthy

curl localhost:17608/ready        # theopenlane readiness (200)
curl localhost:8000/healthz       # BFF liveness (200)
curl localhost:8000/readyz        # BFF -> L1 wire (200 when core reachable, else 503)

docker compose logs -f core       # troubleshoot core boot
docker compose down               # stop (add -v to drop pg/redis volumes)
```

## Image pinning

`core` is pinned to `v1.20.6` to track vendored SHA `a76ccb5c` (ADR-0001). Verify the
exact tag/digest against GHCR and record in `docs/upstream-watch.md`. `RIVERBOAT_TAG`
defaults to `arm64-latest` (Apple Silicon); set it for amd64 hosts.

# Celestia API — FastAPI orchestration / BFF layer

Celestia-domain orchestration in front of the **theopenlane/core** L1 substrate
(Go service, GraphQL on `:17608`). Per [ADR-0001](../adr/0001-fork-theopenlane-core-as-l1-substrate.md)
and [ADR-0012](../adr/0012-fastapi-theopenlane-contract.md):

- GraphQL is the **only** integration boundary with theopenlane (`app/clients/openlane.py`).
- The BFF is the **OpenFGA authorization enforcement point** for cross-org scoping.
- This layer never patches upstream Go.

## Layout

```
app/
  config.py            pydantic-settings (CELESTIA_* env vars)
  clients/openlane.py  the one module that talks theopenlane GraphQL
  api/health.py        /healthz (liveness), /readyz (BFF->L1 wire check)
  api/trust/  api/rls/ Phase-4 trust layer stubs (MARKED-FOR-EXTERNAL-REVIEW)
tests/                 pytest (httpx ASGITransport)
```

## Develop

```bash
uv sync                       # install (fetches Python 3.12)
uv run pytest                 # run tests
uv run uvicorn app.main:app   # run locally (expects theopenlane reachable for /readyz)
```

In docker-compose the service resolves `core`, `openfga`, `dex` by name; see
`../cross-cutting/deploy/docker-compose.yml`.

## Roadmap (Phase 1)

M1 (this slice) — health proxy. Next: M2 auth/tetrad, M3 framework loader,
M4 domain endpoints, M5 smoke test. See the plan and `../ROADMAP.md`.

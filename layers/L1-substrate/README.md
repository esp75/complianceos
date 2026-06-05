# L1 — Substrate

theopenlane/core fork extension points. See [ADR-0001](../../adr/0001-fork-theopenlane-core-as-l1-substrate.md).

## Role

Foundational compliance entities (Organizations, Users, Frameworks, Controls, Evidence, Procedures, Policies, Questionnaires) + authentication (SSO/OIDC/Passkeys) + authorization (OpenFGA) + audit log (Entgo auto-history) + GraphQL API.

## Boundary

This folder contains:

- Celestia's space-Framework definitions (YAML/JSON loaded by theopenlane at startup).
- Celestia's data-model extensions (new Evidence types, new Control attributes).
- Celestia's OpenFGA authorization model for the 4-role tetrad.

It does NOT contain:

- Patches to upstream Go files. Modifications go through theopenlane's Framework/Control/Plugin extension surface.
- Application logic. Business workflows go in `app/api/` (FastAPI orchestration).

## Sub-folders

- `frameworks/` — Celestia-authored Openlane Frameworks
  - `eu-space-act/` — Articles 1–N of EU Space Act, parsed into Openlane Framework schema
  - `iso-24113/` — ISO 24113 disposal & space-debris-mitigation requirements
  - `itu/` — ITU Radio Regulations relevant articles (9, 11, 21, 22)
- `extensions/` — type extensions, OpenFGA model, custom evidence types

## Phase 1 deliverables (see ROADMAP.md)

- [x] Hand-author the three Framework YAMLs (EU Space Act, ISO 24113, ITU) — loaded into
      theopenlane via `app/app/loaders/framework_loader.py` (Framework→Standard,
      Control→Control, `spec.controls[]`→Subcontrol). 13 controls, 22 subcontrols.
- [x] OpenFGA model: operator | insurer | regulator | admin — via groups + tuples
      (ADR-0012), see [`../cross-cutting/README.md`](../cross-cutting/README.md) and
      `cross-cutting/auth/`. (M2)
- [x] SSO/OIDC: theopenlane built-in auth + Dex for dev; EU IdP (Authentik/Keycloak)
      deferred to Phase 4 (needs per-org SSO enforcement). (M2)
- [x] docker-compose dev environment: theopenlane + Postgres + OpenFGA + redis + dex
      (`cross-cutting/deploy/`). AGE + pgvector are a separate `kg-postgres` (M6, Phase 3).
- [x] FastAPI orchestration layer scaffold under `app/` proxying to GraphQL. (M1/M2)
- [x] End-to-end smoke test (operator creates Evidence linked to a Framework Control →
      regulator lists it + downloads audit history) — `app/tests/test_smoke_e2e.py` (opt-in)
      + regulator portal stub at `GET /portal`. (M5)

## Skills to invoke

- `fastapi-expert` for the FastAPI orchestration layer
- `postgres-pro` for AGE + pgvector tuning
- `mcp-developer` if extending gbrain with code-surface introspection of theopenlane

## Upstream reference

- Code: `external/theopenlane-core/` at SHA `a76ccb5c35955ed8cb364a7aab65cec9808b854a`
- Docs to read first: README, ARCHITECTURE.md (in upstream), and the GraphQL schema files
- Watch for: schema-breaking changes between releases — track in `docs/upstream-watch.md` (future)

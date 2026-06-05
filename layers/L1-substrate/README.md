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

- [ ] Hand-author the three Framework YAMLs (EU Space Act, ISO 24113, ITU)
- [ ] OpenFGA model: operator | insurer | regulator | admin × Organization × Framework × Evidence
- [ ] SSO/OIDC config for Authentik or Keycloak (EU-hosted)
- [ ] docker-compose dev environment: theopenlane + Postgres + AGE + pgvector
- [ ] FastAPI orchestration layer scaffold under `app/api/` proxying to GraphQL
- [ ] End-to-end smoke test (create Org → upload Evidence → Evidence linked to Framework Control)

## Skills to invoke

- `fastapi-expert` for the FastAPI orchestration layer
- `postgres-pro` for AGE + pgvector tuning
- `mcp-developer` if extending gbrain with code-surface introspection of theopenlane

## Upstream reference

- Code: `external/theopenlane-core/` at SHA `a76ccb5c35955ed8cb364a7aab65cec9808b854a`
- Docs to read first: README, ARCHITECTURE.md (in upstream), and the GraphQL schema files
- Watch for: schema-breaking changes between releases — track in `docs/upstream-watch.md` (future)

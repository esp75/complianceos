# Upstream watch

Tracks the relationship between vendored source SHAs (`external/VENDOR.md`) and the
container image tags we deploy, plus schema-break risks to watch on upgrade.

## Image ↔ SHA pins

| Component | Vendored SHA | Deployed image tag | Status |
|---|---|---|---|
| theopenlane/core | `a76ccb5c` (2026-05-14) | `ghcr.io/theopenlane/core:v1.20.6` | ⚠️ **verify** — tag chosen because ADR-0001 cites v1.20.6 (released ~3 days before the SHA). The SHA is a few commits past the v1.20.6 tag on `main`. Confirm the exact tag/digest at-or-before `a76ccb5c` on GHCR and pin by digest. |
| openfga/openfga | n/a (image only) | `v1.15.1` | ✅ from upstream `docker-compose-fga.yml` |
| redis | n/a | `7.4.9-alpine` | ✅ from upstream `docker-compose-redis.yml` |
| dexidp/dex | n/a | `v2.45.1` | ✅ from upstream `docker-compose.yml` |
| theopenlane/riverboat | n/a | `arm64-latest` (`RIVERBOAT_TAG`) | ⚠️ arch-floating tag — pin a digest for reproducibility |
| kg-postgres base (pgvector) | n/a | `pgvector/pgvector:pg17` | ✅ multi-arch; pgvector 0.8.2 ships built |
| Apache AGE (in kg-postgres) | n/a | source `release/PG17/1.7.0` | ✅ compiled from source on the pgvector base; PG17 supported as of AGE 1.7.0. Pin a tag/commit when AGE cuts a PG17 release tag (currently only a release branch). |

## Schema-break risk on core upgrade

- The Celestia framework loader (M3) and BFF (M4) target theopenlane's GraphQL schema
  (`createStandard`/`createControl`/`createSubcontrol`/`createEvidence`). A core SHA/tag
  bump can change these inputs. On any bump: regenerate/re-test the loader against the
  new `internal/graphapi/schema/ent.graphql` before deploying.
- The embedded OpenFGA model (`fga/model/model.fga`) can change role/relation names that
  the tetrad-via-groups approach (ADR-0012, M2) builds on. Diff it on upgrade.

## Dev-only deviations from upstream defaults (revisit for production)

- `core` runs as `user: "0:0"` in dev so it can self-generate ephemeral JWT keys in its
  CWD. Production: run nonroot and supply keys via a mounted keywatcher `KeyDir`.
- `riverboat` uses a placeholder `openlaneapitoken`. Production: mint a real PAT.
- All DB/session/authz secrets in `cross-cutting/deploy/config/.config.yaml` are the
  upstream dev placeholders. Production: inject via secrets, never commit.

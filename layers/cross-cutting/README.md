# Cross-cutting

Auth, observability, deploy. See [ADR-0001](../../adr/0001-fork-theopenlane-core-as-l1-substrate.md) (auth), [ADR-0007](../../adr/0007-postgres-age-pgvector-as-production-kg-substrate.md) (storage).

## Role

Concerns that span every layer: who can do what (auth), how we know it's working (observability), and where it runs (deploy).

## Sub-folders

- `auth/` — the operator/insurer/regulator/admin tetrad realized on top of theopenlane/core's auth surface via OpenFGA **groups + tuples** (not a custom model). See [`tetrad-roles.md`](../../cross-cutting/auth/tetrad-roles.md) and [`seed-tuples.yaml`](../../cross-cutting/auth/seed-tuples.yaml).
- `observability/` — Prometheus rules, Grafana dashboards, Loki log-pipeline configs. All EU-hosted.
- `deploy/` — docker-compose.yml, Coolify configuration, nginx ingress, LetsEncrypt automation.

## Auth model (tetrad via groups, ADR-0012)

theopenlane's embedded OpenFGA model is auto-written on startup and must not be patched
(ADR-0001). It ships `organization` roles `admin/member/owner` and an object-creator
pattern (`<obj>_creator: [group#member]`, `can_create_<obj>: can_edit or <obj>_creator`).
The tetrad is built **on top** of these primitives with groups + relationship tuples —
no custom `organization#operator/#insurer/#regulator` types (those would require a fork).

| Tetrad role | org role | extra | net capability |
|---|---|---|---|
| admin | `ADMIN` | `audit_log_viewer` tuple | create + read + audit |
| operator | `MEMBER` | Operators group = evidence/control/standard creator | `can_create_*`, read |
| insurer | `MEMBER` | — | read only (BFF scopes to underwritten orgs) |
| regulator | `MEMBER` | `audit_log_viewer` tuple | read + audit (BFF scopes by jurisdiction) |

Cross-org scoping (which orgs an insurer/regulator may see) is **not expressible in the
upstream model** and is enforced at the BFF boundary (`app/clients/openfga.py`), per
ADR-0012. The mapping spec is [`cross-cutting/auth/tetrad-roles.md`](../../cross-cutting/auth/tetrad-roles.md);
the executable seeder is `app/app/auth/seed_tetrad.py` (verified by OpenFGA `/check`).

## Observability targets (Phase 4)

- Prometheus metrics: API p50/p99 latency, evidence ingestion rate, drafting agent latency + cost, conjunction-event throughput.
- Grafana dashboards: per-Org compliance status, per-Framework Control coverage, retrieval P@5 over time, LLM token spend by Org.
- Loki log streams: structured JSON logs for every theopenlane GraphQL call, every L4 drafting decision, every trust-layer signing event.

## Deploy

- **Infra**: Hetzner DE. Bare-metal or cloud as cost dictates.
- **Orchestrator**: Coolify (self-hosted PaaS) on Hetzner. Reproducible from `deploy/` config.
- **DB**: Hetzner-managed Postgres 17 with AGE + pgvector extensions enabled.
- **Object storage**: Hetzner Object Storage (S3-compatible, EU).
- **Ingress**: nginx + LetsEncrypt automation.
- **No US-hosted services** for application data or identity.

## Skills to invoke

- `kubernetes-specialist` — even if not running K8s, the patterns apply to Coolify
- `/setup-deploy` — wire up `/land-and-deploy` for the Coolify target
- `/cso` — quarterly comprehensive deploy + auth audit
- `/canary` — post-deploy health verification

## Open questions

- Backup target: Hetzner Object Storage cross-region replication or external EU provider (BackBlaze EU, Wasabi EU). Default: Hetzner Object Storage cross-DC.
- GPU inference host: Hetzner GPU instances or alternative EU GPU cloud (Scaleway, OVH). Default: Hetzner GPU once Phase 3 model training begins.

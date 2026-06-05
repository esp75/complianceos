# Cross-cutting

Auth, observability, deploy. See [ADR-0001](../../adr/0001-fork-theopenlane-core-as-l1-substrate.md) (auth), [ADR-0007](../../adr/0007-postgres-age-pgvector-as-production-kg-substrate.md) (storage).

## Role

Concerns that span every layer: who can do what (auth), how we know it's working (observability), and where it runs (deploy).

## Sub-folders

- `auth/` — OpenFGA model definitions for the operator/insurer/regulator/admin tetrad. Backed by theopenlane/core's auth surface.
- `observability/` — Prometheus rules, Grafana dashboards, Loki log-pipeline configs. All EU-hosted.
- `deploy/` — docker-compose.yml, Coolify configuration, nginx ingress, LetsEncrypt automation.

## Auth model (high-level)

```
type Organization
type Framework
type Control
type Evidence
type User

relations:
  Organization#member          -> User
  Organization#operator        -> User
  Organization#insurer         -> User
  Organization#regulator       -> User
  Organization#admin           -> User
  Framework#org                -> Organization
  Control#framework            -> Framework
  Evidence#org                 -> Organization
  Evidence#control             -> Control

policies:
  operator   can read/write Evidence within their Org
  insurer    can read Evidence + risk scores across Orgs they have a contract with
  regulator  can read Evidence + audit logs across Orgs they have jurisdiction over
  admin      can read/write all
```

(Full model in `auth/openfga.model.fga` — future, Phase 1.)

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

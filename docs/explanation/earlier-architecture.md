# The earlier architecture (v0.1 layers)

The repository began as a broader platform: a compliance system built on an open-source GRC substrate,
with a knowledge graph, an orbital-debris risk engine, a drafting agent and dashboards. That design is
still in the repository, under [`layers/`](../../layers/), and some of its code is still used. It is
**not** what the planner is.

## What is where

| Layer | Folder | Status |
|---|---|---|
| L1 substrate (theopenlane/core, OpenFGA) | `external/`, `layers/L1-substrate/` | Used in team mode |
| L2 knowledge graph (Postgres, AGE, pgvector) | `layers/L2-knowledge-graph/`, `app/app/kg/` | Partly used by the drafting code |
| L3 orbital engine (Orekit service, risk scoring) | `layers/L3-sder-engine/` | Parked (ADR-0017) |
| L4 drafting agent | `layers/L4-drafting-agent/`, `app/app/l4/` | Its citation check is used by the planner's brief |
| L5 dashboards (openmct) | `layers/L5-dashboard/` | Parked (ADR-0017) |
| Cross-cutting (team deployment, auth model) | `cross-cutting/` | Used in team mode |

[ADR-0017](../../adr/0017-first-product-refocus.md) parked the orbital and dashboard layers. The planner
keeps the parts it needs and leaves the rest in place, so the history stays intact.

## Naming

Code and configuration still use the prefix `CELESTIA_`, from the project's original name. It is a
historical name, not a separate product. It is kept so that existing deployments and the code's history
keep working. See [configuration](../reference/configuration.md).

## Gbrain

Some scripts and notes refer to an agent-memory store called gbrain. It is an internal development tool,
not a runtime dependency of the planner. Nothing in the planner requires it.

## Reading the layer docs

Each layer has its own README. They were written for the earlier design, so read them as history. For
what the current product does, start with [architecture](architecture.md).

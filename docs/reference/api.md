# HTTP API reference

The API is FastAPI. Its complete, generated OpenAPI schema is the source of truth:

- **Live:** with the stack running, interactive docs are at <http://localhost:8001/docs>.
- **Checked in:** [`web/openapi.json`](../../web/openapi.json), used to generate the web app's types.

The planner endpoints are the ones most users need. They have no path prefix.

## Knowledge

| Method | Path | Purpose |
|---|---|---|
| GET | `/knowledge/jurisdictions` | List jurisdictions in the knowledge pack |
| GET | `/knowledge/licenses/{license_id}` | One licence record, with its citations |
| GET | `/knowledge/facilitators` | Firms that help with licensing |

## Missions and roadmaps

| Method | Path | Purpose |
|---|---|---|
| POST | `/roadmap` | Compute a roadmap from a profile without saving it |
| GET | `/missions` | List missions |
| POST | `/missions` | Create a mission (returns `201`) |
| POST | `/missions/sample` | Create the sample mission (returns `201`) |
| GET | `/missions/{mission_id}` | Get a mission |
| PUT | `/missions/{mission_id}` | Replace a mission's profile |
| DELETE | `/missions/{mission_id}` | Delete a mission (returns `204`) |
| GET | `/missions/{mission_id}/roadmap` | The roadmap for a saved mission |
| POST | `/missions/{mission_id}/brief` | The brief. `?ai=true` asks Claude to write the summary (see [how-to](../how-to/enable-claude-summaries.md)) |
| POST | `/missions/{mission_id}/intro-email` | A drafted first email to an authority or firm |

## Tracker, deadlines and exports

| Method | Path | Purpose |
|---|---|---|
| GET | `/missions/{mission_id}/applications` | Applications for a mission |
| POST | `/missions/{mission_id}/applications` | Add an application (returns `201`) |
| PATCH | `/applications/{app_id}` | Change an application's state or dates |
| GET | `/applications/{app_id}/events` | State history of an application |
| GET | `/applications/{app_id}/contacts` | Contact log for an application |
| POST | `/applications/{app_id}/contacts` | Log a contact (returns `201`) |
| GET | `/missions/{mission_id}/deadlines` | Deadlines across the mission |
| GET | `/missions/{mission_id}/calendar.ics` | Calendar export |
| GET | `/missions/{mission_id}/dossier.pdf` | Dossier PDF (signed when a seed is set; the signature covers roadmap and brief) |
| GET | `/missions/{mission_id}/dossier.signed.json` | The signed dossier data on its own, for offline verification |
| GET | `/program` | The workspace's missions folded into one row per jurisdiction, plus the per-owner workload and the next dates |
| GET, PUT | `/alerts/recipients` | This workspace's Watch digest recipients (empty = deployment default) |

## The Watch

Changes in the public sources the knowledge pack cites, filtered to what the workspace tracks ([ADR-0019](../../adr/0019-the-watch-v0.md)).

| Method | Path | Purpose |
|---|---|---|
| GET | `/watch/changes` | Source changes that touch this workspace's applications, newest first |
| GET | `/missions/{mission_id}/watch` | The same, for one mission |
| POST | `/watch/run` | Check every cited source once and record changes (`can_create_evidence` in team mode) |

## Reviewer package

| Method | Path | Purpose |
|---|---|---|
| GET | `/missions/{mission_id}/dossier.md` | Dossier as stable Markdown with a reviewer checklist ([ADR-0022](../../adr/0022-dossier-sections-and-review-package.md)) |

## History and usage

| Method | Path | Purpose |
|---|---|---|
| POST | `/history/export` | Signed, checkpointed export of every application event in the workspace ([ADR-0021](../../adr/0021-signed-history-and-pilot-usage.md)) |
| GET | `/missions/{mission_id}/history` | Signed export for one mission (not chained) |
| POST | `/usage` | Record that a feature was used (`kind` only) |
| GET | `/usage/summary?days=30` | Counts per kind and active days |

## Other

| Method | Path | Purpose |
|---|---|---|
| GET | `/healthz` | Liveness |
| GET | `/readyz` | Readiness, including the database |
| GET | `/auth/me`, `/auth/can` | Current user and permission checks (see [configuration](configuration.md)) |
| POST | `/bundle/sign` | Sign an evidence bundle (see [trust, signing and the threat model](../explanation/trust-and-signing.md)) |

Responses use the status codes shown above. A brief that fails citation grounding returns `422`;
an AI brief without a configured key returns `503`.

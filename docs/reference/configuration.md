# Configuration reference

Settings come from the environment, or from a `.env` file next to `compose.yaml`. Copy
[`.env.example`](../../.env.example) to start. Every setting is optional for a local run.

## Variables in `.env`

| Variable | Default | Effect |
|---|---|---|
| `POSTGRES_PASSWORD` | `local-dev-only` | Password for the local Postgres container. Change it if the port is reachable beyond your machine. |
| `TRUST_SIGNING_SEED` | empty | 64 hex characters. When set, dossiers are Ed25519-signed. When empty, they are exported unsigned. See [how-to](../how-to/enable-signed-dossiers.md). |
| `ANTHROPIC_API_KEY` | empty | Enables Claude-written briefs. See [how-to](../how-to/enable-claude-summaries.md). |
| `REPO_URL` | empty | Public repository URL, used for "suggest a correction" links in the web app. |

## Settings inside the API

Compose maps the variables above into the API's environment. The API reads its own settings with the
prefix `CELESTIA_` (the project's original name). Defined in
[`app/app/config.py`](../../app/app/config.py).

| Setting | Default | Notes |
|---|---|---|
| `CELESTIA_KG_DSN` | Postgres URL | Database connection. Compose sets it. When no Postgres is reachable, the API falls back to an in-memory store. |
| `CELESTIA_AUTH_MODE` | set by Compose (`local`) | Single-user local mode. Team mode is described in [`cross-cutting/deploy/`](../../cross-cutting/deploy/). |
| `CELESTIA_LOCAL_ALLOWED_NETWORKS` | set by Compose | Networks allowed to use local mode. |
| `CELESTIA_ANTHROPIC_API_KEY` | empty | Set from `ANTHROPIC_API_KEY` by Compose. |
| `CELESTIA_ANTHROPIC_MODEL` | `claude-opus-4-7` | Model used for Claude-written briefs. |
| `CELESTIA_ANTHROPIC_BASE_URL` | `https://api.anthropic.com` | Override for a different Anthropic endpoint. |
| `CELESTIA_TRUST_SIGNING_SEED` | empty | Set from `TRUST_SIGNING_SEED` by Compose. |
| `CELESTIA_PG_TEST_DSN` | unset | Enables the Postgres store tests. See [run the tests](../how-to/run-tests.md). |

## Ports

| Service | Host address |
|---|---|
| Web app | `127.0.0.1:3000` |
| API | `127.0.0.1:8001` |

Both bind to loopback only, so nothing is exposed to your network by default.

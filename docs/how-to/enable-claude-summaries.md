# How to enable Claude-written summaries

The brief's executive summary can be written by Claude. This is optional. The planner is fully
deterministic without it, and nothing leaves your machine unless you add a key.

## 1. Add a key

In the `.env` file next to `compose.yaml`:

```bash
ANTHROPIC_API_KEY=<your key>
```

Restart the stack with `docker compose up -d`. Compose passes the key to the API as
`CELESTIA_ANTHROPIC_API_KEY`.

## 2. Request an AI-written brief

The brief endpoint takes an `ai` flag:

```bash
curl -X POST "http://localhost:8001/missions/<mission-id>/brief?ai=true"
```

Without a key the endpoint returns `503` and names the missing setting. Without `ai=true` you get the
deterministic brief, as before.

## What the check does

Claude's summary is accepted only if it cites the roadmap's own sources, and every paragraph cites at
least one of them. If it does not, the endpoint returns `422` with the reason, and the summary is not
shown. The same check guards the compliance-drafting endpoint.

## Notes

- The model is set by `CELESTIA_ANTHROPIC_MODEL` (see [configuration](../reference/configuration.md)).
- The MVP policy is to use Anthropic models only; see
  [ADR-0010](../../adr/0010-mvp-llm-policy-claude-only.md).

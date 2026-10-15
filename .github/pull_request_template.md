## What changes

## Checklist

- [ ] Tests pass (`cd app && uv run pytest`, `cd web && bun test`)
- [ ] For knowledge changes: `uv run python -m app.planner.knowledge validate` passes, every new
      citation quotes the official text with its URL and retrieval date, and unverifiable items are
      left out or marked `estimate`
- [ ] No files under `app/app/api/trust/**` or `app/app/api/bundle/sign*.py` changed (they need
      the external-review process in CLAUDE.md)

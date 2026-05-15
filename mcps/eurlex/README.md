# celestia-mcp-eurlex

MCP server that watches and searches EUR-Lex (the official EU legal information service).

## Tools

- `health()` — liveness check.

Planned (Phase 2):

- `search(query: str, celex_type: str | None) -> list[Document]`
- `fetch_celex(celex_id: str) -> Document`
- `watch(celex_ids: list[str], since: date) -> list[Diff]`

## Run

```
uv run python -m eurlex_mcp
```

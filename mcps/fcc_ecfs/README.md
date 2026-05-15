# celestia-mcp-fcc-ecfs

MCP server: FCC Electronic Comment Filing System (ECFS) watcher.

## Tools

- `health()` — liveness check.

Planned:

- `search_proceedings(query: str) -> list[Proceeding]`
- `list_filings(docket: str, since: date) -> list[Filing]`
- `download_filing(filing_id: str) -> bytes`

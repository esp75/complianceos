# celestia-mcp-gitleaks

MCP server: gitleaks CLI wrapped for secrets scanning.

## Tools

- `health()` — liveness check.

Planned:

- `scan_repo(path: str) -> ScanReport`
- `scan_commit(repo: str, sha: str) -> ScanReport`

# celestia-mcp-semgrep

MCP server: Semgrep CLI wrapped so `/cso` can call SAST as a tool.

## Tools

- `health()` — liveness check.

Planned:

- `scan(path: str, config: str = "auto") -> ScanReport`
- `list_rules() -> list[Rule]`

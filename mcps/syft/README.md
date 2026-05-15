# celestia-mcp-syft

MCP server: Syft SBOM generator wrapped for supply-chain inventory.

## Tools

- `health()` — liveness check.

Planned:

- `generate_sbom(path: str, format: str = "spdx-json") -> SBOM`
- `diff_sbom(old: str, new: str) -> SBOMDiff`

"""Semgrep MCP server. Phase 0 scaffold — health-check only."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("celestia-semgrep")


@mcp.tool()
def health() -> dict[str, str]:
    """Liveness check."""
    return {"status": "ok", "server": "celestia-semgrep"}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()

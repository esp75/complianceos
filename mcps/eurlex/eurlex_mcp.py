"""EUR-Lex MCP server (FastMCP). Phase 0 scaffold — health-check only."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("celestia-eurlex")


@mcp.tool()
def health() -> dict[str, str]:
    """Liveness check."""
    return {"status": "ok", "server": "celestia-eurlex"}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()

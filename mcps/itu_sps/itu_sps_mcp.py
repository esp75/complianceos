"""ITU SNS MCP server. Phase 0 scaffold — health-check only.

Requires ITU credentials before extending. See README.md.
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("celestia-itu-sps")


@mcp.tool()
def health() -> dict[str, str]:
    """Liveness check."""
    return {"status": "ok", "server": "celestia-itu-sps"}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()

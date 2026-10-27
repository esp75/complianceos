"""EUR-Lex MCP server (FastMCP). Tools: health, fetch_celex, verify_citation.

search() from the Phase 1 plan is not implemented yet. CELLAR SPARQL is the planned route.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from eurlex_core import CelexError, EurLexClient

mcp = FastMCP("celestia-eurlex")
_client = EurLexClient()


@mcp.tool()
def health() -> dict[str, str]:
    """Liveness check."""
    return {"status": "ok", "server": "celestia-eurlex"}


@mcp.tool()
def fetch_celex(celex: str, lang: str = "EN") -> dict[str, Any]:
    """Fetch the consolidated text of a CELEX document (cached on disk)."""
    try:
        doc = _client.fetch_celex(celex, lang)
    except CelexError as exc:
        return {"error": str(exc)}
    return {"celex": doc.celex, "lang": doc.lang, "source_url": doc.url, "chars": len(doc.text)}


@mcp.tool()
def verify_citation(celex: str, article: str, paragraph: str | None = None) -> dict[str, Any]:
    """Check that an article exists in the given CELEX text. Paragraph is not checked."""
    v = _client.verify_citation(celex, article, paragraph)
    return {"verified": v.verified, "reason": v.reason, "source_url": v.url}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()

"""Real MCP server (stdio): keyword search over SOP documents.  python -m mcp_servers.docs_server.server"""
import os
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from mcp_servers.logic import DocIndex

DOCS_DIR = os.getenv("DOCS_DIR") or str(Path(__file__).resolve().parents[2] / "data" / "docs")
mcp = FastMCP("docs-server")
_index = DocIndex(DOCS_DIR)


@mcp.tool()
def search_docs(query: str, k: int = 3) -> str:
    """Search company SOPs and policies. Returns the best matching paragraphs, each prefixed with [file name]."""
    return _index.search(query, k)


if __name__ == "__main__":
    mcp.run()

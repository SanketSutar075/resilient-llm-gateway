"""Real MCP server (stdio). Run by the agent as a subprocess:  python -m mcp_servers.calc_server.server"""
from mcp.server.fastmcp import FastMCP
from mcp_servers.logic import safe_calc

mcp = FastMCP("calc-server")


@mcp.tool()
def calculate(expression: str) -> str:
    """Evaluate an arithmetic expression such as '14/200*100'. Deterministic. Use it for ALL math."""
    return safe_calc(expression)


if __name__ == "__main__":
    mcp.run()

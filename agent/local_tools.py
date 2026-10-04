"""Same tools as the MCP servers, but as plain Python functions (offline tests, no subprocess)."""
from pathlib import Path
from agent.tools import Tool, ToolRegistry
from mcp_servers.logic import DocIndex, safe_calc

DEFAULT_DOCS = Path(__file__).resolve().parents[1] / "data" / "docs"


def build_local_registry(docs_dir: str | Path = DEFAULT_DOCS) -> ToolRegistry:
    index = DocIndex(docs_dir)
    reg = ToolRegistry()
    reg.register(Tool("calculate", "Evaluate an arithmetic expression. Use for ALL math.",
                      {"expression": "e.g. 14/200*100"}, lambda expression: safe_calc(expression)))
    reg.register(Tool("search_docs", "Search company SOPs and policies.",
                      {"query": "search words", "k": "number of results"},
                      lambda query, k=3: index.search(query, int(k)), optional={"k"}))
    counter = {"n": 0}

    def create_ticket(title: str, details: str) -> str:
        counter["n"] += 1
        return f"TICKET-{counter['n']:04d} created: {title}"

    reg.register(Tool("create_ticket", "Create a maintenance / NCR ticket.",
                      {"title": "short title", "details": "what happened"}, create_ticket,
                      requires_approval=True))
    return reg

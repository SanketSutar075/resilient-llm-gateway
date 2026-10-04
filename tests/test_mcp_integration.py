"""Starts the REAL MCP servers as subprocesses. Skipped automatically if the mcp package is missing."""
import json
import pytest

pytest.importorskip("mcp")
from agent.loop import Agent
from agent.mcp_client import MCPToolRegistry
from gateway.providers.scripted import ScriptedProvider
from gateway.router import Router
from state.store import InMemoryStore


@pytest.fixture(scope="module")
def reg():
    with MCPToolRegistry() as r:
        yield r


def test_tools_discovered_from_real_servers(reg):
    assert {"calculate", "search_docs"} <= set(reg.tools)
    assert "expression" in reg.tools["calculate"].params
    assert "k" in reg.tools["search_docs"].optional


def test_call_real_calc_and_docs_tools(reg):
    assert reg.tools["calculate"].fn(expression="12*(3+4)") == "84"
    out = reg.tools["search_docs"].fn(query="reject rate escalation")
    assert "escalation_rules.md" in out


def test_real_tool_error_is_raised_and_agent_survives(reg):
    p = ScriptedProvider("openai", [json.dumps({"tool": "calculate", "args": {"expression": "1/0"}}),
                                    json.dumps({"final": "cannot divide"})])
    agent = Agent(Router([p], sleep=lambda s: None), InMemoryStore(), reg)
    r = agent.run("q")
    assert r.ok and "division by zero" in r.steps[0]["result"]


def test_agent_with_failover_over_real_mcp_tools(reg):
    t1 = json.dumps({"tool": "search_docs", "args": {"query": "porosity reject rate"}})
    t2 = json.dumps({"tool": "calculate", "args": {"expression": "14/200*100"}})
    openai = ScriptedProvider("openai", [t1], die_after=1)
    claude = ScriptedProvider("claude", [t2, json.dumps({"final": "7% > 2% limit"})])
    agent = Agent(Router([openai, claude], sleep=lambda s: None), InMemoryStore(), reg)
    r = agent.run("14 of 200 parts rejected for porosity. Within limit?")
    assert r.ok and r.providers == ["openai", "claude"]
    assert "casting_defects_sop.md" in r.steps[0]["result"] and r.steps[1]["result"] == "7"

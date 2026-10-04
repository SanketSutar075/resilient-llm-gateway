"""Offline demo of Step 8. No API keys. OpenAI answers once, then its quota ends; Claude finishes the task.
  python agent_demo.py          -> tools run as local Python functions
  python agent_demo.py --mcp    -> tools run through REAL MCP servers (subprocess over stdio)"""
import json
import sys
from agent.local_tools import build_local_registry
from agent.loop import Agent
from gateway.providers.scripted import ScriptedProvider
from gateway.router import Router
from state.store import InMemoryStore


def call(name, **args):
    return json.dumps({"tool": name, "args": args})


openai = ScriptedProvider("openai", [call("search_docs", query="pour temperature range")], die_after=1)
claude = ScriptedProvider("claude", [
    call("search_docs", query="porosity reject rate limit"),
    call("calculate", expression="14/200*100"),
    json.dumps({"final": "Pour temp 690C is below the 700-730C range [pour_temperature_policy.md]. "
                         "Reject rate is 7%, above the 2% porosity limit [casting_defects_sop.md] and above 5%, "
                         "so an NCR must be raised [escalation_rules.md]."}),
])
router = Router([openai, claude], sleep=lambda s: None)
registry = build_local_registry() if "--mcp" not in sys.argv else None
if registry is None:
    from agent.mcp_client import MCPToolRegistry
    registry = MCPToolRegistry()
    print("(tools served by real MCP servers: " + ", ".join(registry.tools) + ")")

agent = Agent(router, InMemoryStore(), registry, role="an industrial QC assistant")
task = "Line 3: pour temperature was 690C and 14 of 200 parts were rejected for porosity. Is this OK? What does the SOP say?"
print("TASK:", task, "\n")
result = agent.run(task)
for i, s in enumerate(result.steps, 1):
    print(f"step {i} [{s['provider']}] {s['tool']}({s['args']})\n        -> {s['result'][:90]!r}")
print(f"\nProviders used in order: {result.providers}   failover events: {result.failover_events}")
print("ANSWER:", result.answer)
if hasattr(registry, "close"):
    registry.close()

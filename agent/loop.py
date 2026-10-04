"""Step 8: the agent loop. It runs on top of ChatSession, so a provider failure in the middle of a task
does not stop it: the next provider gets the full history including earlier tool results."""
from dataclasses import dataclass, field
from typing import Callable
from agent.protocol import build_system_prompt, parse_action
from agent.tools import ToolRegistry
from gateway.router import Router
from gateway.session import ChatSession


@dataclass
class AgentResult:
    ok: bool
    answer: str | None = None
    reason: str = ""
    steps: list[dict] = field(default_factory=list)       # every tool call: tool, args, result, provider
    providers: list[str] = field(default_factory=list)    # providers that answered, in order, no duplicates in a row
    failover_events: int = 0


class Agent:
    def __init__(self, router: Router, store, registry: ToolRegistry, session_id: str = "agent",
                 role: str = "a helpful assistant", max_steps: int = 6, max_invalid: int = 2,
                 max_result_chars: int = 2000, approver: Callable[[str, dict], bool] | None = None):
        self.registry = registry
        self.session = ChatSession(router, store, session_id, system_prompt=build_system_prompt(registry, role))
        self.max_steps, self.max_invalid, self.max_result_chars = max_steps, max_invalid, max_result_chars
        self.approver = approver  # None = deny every risky tool (safe default)

    def run(self, task: str) -> AgentResult:
        res = AgentResult(ok=False)
        invalid = 0
        resp = self._note(res, self.session.send(task))
        for _ in range(self.max_steps + self.max_invalid + 1):
            action = parse_action(resp.text)
            if action.kind == "final":
                res.ok, res.answer = True, action.text
                return res
            if action.kind == "invalid":
                invalid += 1
                if invalid > self.max_invalid:
                    res.reason = f"model kept returning invalid replies ({action.error})"
                    return res
                resp = self._note(res, self.session.send(
                    'Invalid reply (' + action.error + '). Reply with ONLY JSON: '
                    '{"tool": "<name>", "args": {...}} or {"final": "<answer>"}'))
                continue
            if len(res.steps) >= self.max_steps:
                res.reason = "max_steps reached"
                return res
            result = self._execute(action.name, action.args)
            res.steps.append({"tool": action.name, "args": action.args, "result": result, "provider": resp.provider})
            self.session.add_tool_result(action.name, result)
            resp = self._note(res, self.session.resume())
        res.reason = "max_steps reached"
        return res

    @staticmethod
    def _note(res: AgentResult, resp):
        if not res.providers or res.providers[-1] != resp.provider:
            res.providers.append(resp.provider)
        res.failover_events += len(resp.failovers)
        return resp

    def _execute(self, name: str, args: dict) -> str:
        tool = self.registry.tools.get(name)
        if tool is None:
            return f"ERROR: unknown tool '{name}'. Available: {', '.join(self.registry.tools)}"
        missing = [p for p in tool.params if p not in tool.optional and p not in args]
        if missing:
            return f"ERROR: missing argument(s): {', '.join(missing)}"
        unknown = [a for a in args if a not in tool.params]
        if unknown:
            return f"ERROR: unknown argument(s): {', '.join(unknown)}"
        if tool.requires_approval and not (self.approver and self.approver(name, args)):
            return "DENIED: a human did not approve this action. It was NOT executed."
        try:
            out = str(tool.fn(**args))
        except Exception as e:  # tool errors go back to the model, they must not crash the agent
            return f"ERROR: {e}"
        if len(out) > self.max_result_chars:
            out = out[:self.max_result_chars] + " ...[truncated]"
        return out

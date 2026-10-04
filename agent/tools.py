from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Tool:
    name: str
    description: str
    params: dict[str, str]            # arg name -> short description (all required except those marked optional)
    fn: Callable[..., str]
    requires_approval: bool = False   # risky tools need a human OK before running
    optional: set[str] = field(default_factory=set)


class ToolRegistry:
    def __init__(self):
        self.tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self.tools:
            raise ValueError(f"duplicate tool name: {tool.name}")
        self.tools[tool.name] = tool

    def describe(self) -> str:
        lines = []
        for t in self.tools.values():
            args = ", ".join(f"{k}{'?' if k in t.optional else ''}: {v}" for k, v in t.params.items())
            flag = " [needs human approval]" if t.requires_approval else ""
            lines.append(f"- {t.name}({args}): {t.description}{flag}")
        return "\n".join(lines)

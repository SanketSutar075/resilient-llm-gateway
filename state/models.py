"""Provider-neutral conversation history. This is the ONLY place the real history lives (not inside any model)."""
from typing import Literal
from pydantic import BaseModel


class Turn(BaseModel):
    role: Literal["user", "assistant", "tool"]
    content: str
    tool_name: str | None = None   # set when role == "tool"
    provider: str | None = None    # which provider wrote this assistant turn (useful for audit/dashboard)

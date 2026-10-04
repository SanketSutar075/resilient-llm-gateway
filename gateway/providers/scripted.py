"""Offline provider that replies from a script. Used to test and demo the agent loop without API keys."""
from gateway.errors import ProviderError
from gateway.providers.base import BaseProvider
from gateway.schemas import ChatRequest


class ScriptedProvider(BaseProvider):
    def __init__(self, name: str, replies: list[str], die_after: int | None = None, die_status: int = 402):
        """die_after=N: answer N calls, then fail with die_status forever (simulates quota running out)."""
        self.name, self.model = name, f"scripted-{name}"
        self.replies, self.die_after, self.die_status = list(replies), die_after, die_status
        self.calls, self.requests = 0, []

    def _call(self, req: ChatRequest):
        self.requests.append(req)
        if self.die_after is not None and self.calls >= self.die_after:
            raise ProviderError(self.name, self.die_status, "simulated: quota over")
        self.calls += 1
        if not self.replies:
            raise ProviderError(self.name, 500, "script exhausted")
        return self.replies.pop(0), 10, 5

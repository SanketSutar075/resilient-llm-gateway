"""Fake provider for tests and chaos demos. Lets you force any failure without real API keys."""
from gateway.errors import ProviderError
from gateway.providers.base import BaseProvider
from gateway.schemas import ChatRequest


class FakeProvider(BaseProvider):
    def __init__(self, name: str, fail_status: int | None = -1, reply: str = "ok",
                 fail_times: int | None = None):
        """fail_status: -1 = healthy, None = timeout-style, or HTTP code (429/402/500/400).
        fail_times: fail only the first N calls, then recover (None = fail forever)."""
        self.name = name
        self.model = f"fake-{name}"
        self.fail_status = fail_status
        self.fail_times = fail_times
        self.reply = reply
        self.calls = 0

    def _call(self, req: ChatRequest):
        self.calls += 1
        failing = self.fail_status != -1 and (self.fail_times is None or self.calls <= self.fail_times)
        if failing:
            raise ProviderError(self.name, self.fail_status, "simulated failure")
        return f"{self.reply} (from {self.name})", 10, 5

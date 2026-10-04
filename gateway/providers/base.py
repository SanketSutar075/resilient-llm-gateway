import time
from abc import ABC, abstractmethod
from gateway.schemas import ChatRequest, ChatResponse


class BaseProvider(ABC):
    name: str = "base"
    model: str = ""

    @abstractmethod
    def _call(self, req: ChatRequest) -> tuple[str, int, int]:
        """Return (text, input_tokens, output_tokens). Raise ProviderError on failure."""

    def generate(self, req: ChatRequest) -> ChatResponse:
        start = time.perf_counter()
        text, tin, tout = self._call(req)
        return ChatResponse(
            text=text,
            provider=self.name,
            model=self.model,
            input_tokens=tin,
            output_tokens=tout,
            latency_ms=(time.perf_counter() - start) * 1000,
        )

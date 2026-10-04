import os
from gateway.errors import ProviderError
from gateway.providers.base import BaseProvider
from gateway.schemas import ChatRequest


class ClaudeProvider(BaseProvider):
    name = "claude"

    def __init__(self, model: str | None = None):
        from anthropic import Anthropic
        self.model = model or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
        self.client = Anthropic(timeout=30)

    def _call(self, req: ChatRequest):
        import anthropic
        # Claude takes the system prompt separately, not inside messages. This is why adapters exist.
        system = "\n".join(m.content for m in req.messages if m.role == "system")
        msgs = [m.model_dump() for m in req.messages if m.role != "system"]
        try:
            kwargs = dict(model=self.model, max_tokens=req.max_tokens,
                          temperature=req.temperature, messages=msgs)
            if system:
                kwargs["system"] = system
            r = self.client.messages.create(**kwargs)
            text = "".join(b.text for b in r.content if b.type == "text")
            return text, r.usage.input_tokens, r.usage.output_tokens
        except anthropic.APIStatusError as e:
            raise ProviderError(self.name, e.status_code, str(e)) from e
        except Exception as e:
            raise ProviderError(self.name, None, str(e)) from e

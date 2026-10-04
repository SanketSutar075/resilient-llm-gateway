import os
from gateway.errors import ProviderError
from gateway.providers.base import BaseProvider
from gateway.schemas import ChatRequest


class OpenAIProvider(BaseProvider):
    name = "openai"

    def __init__(self, model: str | None = None):
        from openai import OpenAI  # lazy import: project works even if SDK is missing
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.client = OpenAI(timeout=30)

    def _call(self, req: ChatRequest):
        import openai
        try:
            r = self.client.chat.completions.create(
                model=self.model,
                messages=[m.model_dump() for m in req.messages],
                max_tokens=req.max_tokens,
                temperature=req.temperature,
            )
            u = r.usage
            return r.choices[0].message.content or "", u.prompt_tokens, u.completion_tokens
        except openai.APIStatusError as e:
            raise ProviderError(self.name, e.status_code, str(e)) from e
        except Exception as e:  # timeout, connection error, etc.
            raise ProviderError(self.name, None, str(e)) from e

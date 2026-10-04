"""Run: python demo.py   (needs .env with keys). Kill OpenAI by setting a wrong OPENAI_API_KEY and watch Claude answer."""
import logging
from dotenv import load_dotenv
from gateway.providers.anthropic_adapter import ClaudeProvider
from gateway.providers.openai_adapter import OpenAIProvider
from gateway.router import Router
from gateway.schemas import ChatRequest, Message

load_dotenv()
logging.basicConfig(level=logging.INFO)

router = Router([OpenAIProvider(), ClaudeProvider()])
req = ChatRequest(messages=[
    Message(role="system", content="Be concise."),
    Message(role="user", content="Explain RAG in 2 lines."),
])
r = router.generate(req)
print(f"\nAnswered by: {r.provider} ({r.model}) in {r.latency_ms:.0f} ms | failovers: {r.failovers}")
print(r.text)

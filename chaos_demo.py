"""Offline chaos demo (no API keys). Shows retry, failover, circuit breaker and recovery.
Run: python chaos_demo.py"""
import logging
from gateway.providers.fake import FakeProvider
from gateway.router import Router
from gateway.schemas import ChatRequest, Message

logging.basicConfig(level=logging.WARNING, format="   %(message)s")
REQ = ChatRequest(messages=[Message(role="user", content="hi")])

now = [0.0]
openai = FakeProvider("openai")
claude = FakeProvider("claude")
ollama = FakeProvider("ollama")
router = Router([openai, claude, ollama], sleep=lambda s: None, clock=lambda: now[0])


def run(title):
    r = router.generate(REQ)
    print(f"{title:<42} -> {r.provider:<7} failed={r.failovers} skipped={r.skipped} health={router.health()}")


run("1. all healthy")
openai.fail_status = 429
run("2. OpenAI rate limited (retries, switches)")
openai.fail_status = 402
run("3. OpenAI quota over (402)")
run("4. next request (OpenAI skipped by breaker)")
claude.fail_status = 500
run("5. Claude outage too")
claude.fail_status = 500; ollama.fail_status = -1
run("6. only local Ollama left")
openai.fail_status = -1; claude.fail_status = -1
now[0] += 4000
run("7. providers recovered, probe after cooldown")

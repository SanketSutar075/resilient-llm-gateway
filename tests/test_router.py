import pytest
from gateway.errors import AllProvidersFailed, ProviderError
from gateway.providers.fake import FakeProvider
from gateway.router import Router
from gateway.schemas import ChatRequest, Message

REQ = ChatRequest(messages=[Message(role="user", content="hi")])


class Clock:
    def __init__(self): self.t = 0.0
    def __call__(self): return self.t


def make(providers, **kw):
    sleeps = []
    clock = Clock()
    r = Router(providers, sleep=sleeps.append, clock=clock, **kw)
    return r, sleeps, clock


def test_first_provider_answers_when_healthy():
    a, b = FakeProvider("openai"), FakeProvider("claude")
    r, _, _ = make([a, b])
    out = r.generate(REQ)
    assert out.provider == "openai" and out.failovers == [] and b.calls == 0


@pytest.mark.parametrize("status", [402, 401, 500, 503])
def test_immediate_switch_no_retry(status):
    a, b = FakeProvider("openai", status), FakeProvider("claude")
    r, sleeps, _ = make([a, b])
    out = r.generate(REQ)
    assert out.provider == "claude" and out.failovers == ["openai"]
    assert a.calls == 1 and sleeps == []


def test_429_retries_with_backoff_then_switches():
    a, b = FakeProvider("openai", 429), FakeProvider("claude")
    r, sleeps, _ = make([a, b], max_retries=2, backoff_base_s=0.5)
    out = r.generate(REQ)
    assert out.provider == "claude"
    assert a.calls == 3            # 1 try + 2 retries
    assert sleeps == [0.5, 1.0]    # exponential backoff


def test_429_recovers_on_retry_without_switching():
    a, b = FakeProvider("openai", 429, fail_times=1), FakeProvider("claude")
    r, _, _ = make([a, b])
    out = r.generate(REQ)
    assert out.provider == "openai" and b.calls == 0


def test_no_failover_on_bad_request():
    a, b = FakeProvider("openai", 400), FakeProvider("claude")
    r, _, _ = make([a, b])
    with pytest.raises(ProviderError):
        r.generate(REQ)
    assert b.calls == 0


def test_chain_failover_to_third():
    ps = [FakeProvider("openai", 402), FakeProvider("claude", 500), FakeProvider("ollama")]
    r, _, _ = make(ps)
    out = r.generate(REQ)
    assert out.provider == "ollama" and out.failovers == ["openai", "claude"]


def test_all_fail():
    r, _, _ = make([FakeProvider("openai", 402), FakeProvider("claude", 500)])
    with pytest.raises(AllProvidersFailed):
        r.generate(REQ)


def test_quota_provider_is_skipped_on_next_request():
    a, b = FakeProvider("openai", 402), FakeProvider("claude")
    r, _, _ = make([a, b])
    r.generate(REQ)
    out = r.generate(REQ)
    assert a.calls == 1                      # not called again, breaker is open
    assert out.skipped == ["openai"] and out.provider == "claude"
    assert r.health()["openai"] == "open"


def test_repeated_outage_opens_breaker_after_threshold():
    a, b = FakeProvider("openai", 500), FakeProvider("claude")
    r, _, _ = make([a, b], failure_threshold=3)
    for _ in range(3):
        r.generate(REQ)
    assert r.health()["openai"] == "open"
    r.generate(REQ)
    assert a.calls == 3


def test_provider_recovers_via_half_open_probe():
    a, b = FakeProvider("openai", 500, fail_times=3), FakeProvider("claude")
    r, _, clock = make([a, b], failure_threshold=3)
    for _ in range(3):
        r.generate(REQ)
    assert r.health()["openai"] == "open"
    clock.t = 10_000                          # cooldown over, OpenAI is healthy again
    out = r.generate(REQ)
    assert out.provider == "openai" and r.health()["openai"] == "closed"

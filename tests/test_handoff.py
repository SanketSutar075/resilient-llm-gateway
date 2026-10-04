import pytest
from gateway.errors import AllProvidersFailed
from gateway.providers.fake import FakeProvider
from gateway.router import Router
from gateway.session import ChatSession
from state.handoff import to_messages
from state.models import Turn
from state.store import InMemoryStore, RedisStore


def make_router(*providers):
    return Router(list(providers), sleep=lambda s: None, clock=lambda: 0.0)


def texts(provider):
    return [(m.role, m.content) for m in provider.last_request.messages]


def test_task_continues_on_claude_with_full_history_after_openai_dies():
    openai, claude = FakeProvider("openai"), FakeProvider("claude")
    s = ChatSession(make_router(openai, claude), InMemoryStore(), "t1", system_prompt="Be concise.")
    r1 = s.send("Analyse defect spike on line 3")
    assert r1.provider == "openai"
    s.add_tool_result("db.query", "porosity=14 on 2026-10-03")

    openai.fail_status = 402                       # quota over mid-task
    r2 = s.send("What is the root cause?")
    assert r2.provider == "claude" and r2.failovers == ["openai"]

    got = texts(claude)
    assert got[0] == ("system", "Be concise.")
    flat = "\n".join(c for _, c in got)
    assert "Analyse defect spike on line 3" in flat          # old user turn
    assert "ok (from openai)" in flat                         # old assistant turn written by OpenAI
    assert "porosity=14" in flat                              # tool result survived the switch
    assert got[-1][0] == "user" and "root cause" in got[-1][1]


def test_history_survives_process_restart():
    store = InMemoryStore()                                   # same store = same Redis
    a = FakeProvider("openai")
    ChatSession(make_router(a), store, "t2").send("first question")
    b = FakeProvider("claude")
    ChatSession(make_router(b), store, "t2").send("second question")   # brand new session object
    flat = "\n".join(c for _, c in texts(b))
    assert "first question" in flat and "second question" in flat


def test_all_down_then_resume_without_duplicate_turn():
    a = FakeProvider("openai", 500)
    s = ChatSession(make_router(a), InMemoryStore(), "t3")
    with pytest.raises(AllProvidersFailed):
        s.send("hello")
    assert [t.role for t in s.history()] == ["user"]          # user turn was saved
    a.fail_status = -1
    s.router.breakers["openai"].record_success()
    r = s.resume()
    assert r.provider == "openai"
    assert [t.role for t in s.history()] == ["user", "assistant"]   # exactly one user turn


def test_resume_refuses_when_nothing_pending():
    s = ChatSession(make_router(FakeProvider("openai")), InMemoryStore(), "t4")
    s.send("hi")
    with pytest.raises(ValueError):
        s.resume()


def test_tool_turns_merge_and_start_with_user():
    msgs = to_messages([Turn(role="user", content="a"), Turn(role="tool", tool_name="x", content="r"),
                        Turn(role="user", content="b")])
    assert [m.role for m in msgs] == ["user"]                 # three neighbours merged into one user message
    assert "[Tool result: x]" in msgs[0].content


def test_trimming_never_starts_with_assistant():
    turns = [Turn(role="user", content="u1"), Turn(role="assistant", content="a1"),
             Turn(role="user", content="u2")]
    msgs = to_messages(turns, max_turns=2)                    # trim cuts u1, leaving a1 first
    assert msgs[0].role == "user" and msgs[0].content == "u2"


class FakeRedis:
    def __init__(self): self.d, self.ttl = {}, {}
    def rpush(self, k, v): self.d.setdefault(k, []).append(v)
    def expire(self, k, s): self.ttl[k] = s
    def lrange(self, k, a, b): return list(self.d.get(k, []))
    def delete(self, k): self.d.pop(k, None)


def test_redis_store_roundtrip_and_ttl():
    r = FakeRedis()
    st = RedisStore(client=r, ttl_s=60)
    st.append("s", Turn(role="user", content="hi"))
    st.append("s", Turn(role="assistant", content="yo", provider="claude"))
    got = st.load("s")
    assert [t.content for t in got] == ["hi", "yo"] and got[1].provider == "claude"
    assert r.ttl["chat:s"] == 60
    st.clear("s")
    assert st.load("s") == []

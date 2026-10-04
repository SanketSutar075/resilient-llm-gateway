"""Offline demo of Step 7 (no keys, no Redis). A task starts on OpenAI, OpenAI dies mid-task,
Claude continues WITH the full history and tool result.   Run: python handoff_demo.py"""
from gateway.providers.fake import FakeProvider
from gateway.router import Router
from gateway.session import ChatSession
from state.store import InMemoryStore

openai, claude = FakeProvider("openai"), FakeProvider("claude")
router = Router([openai, claude], sleep=lambda s: None)
session = ChatSession(router, InMemoryStore(), "demo", system_prompt="You are a QC assistant.")

print("USER : Defects spiked on line 3. Check the data.")
r = session.send("Defects spiked on line 3. Check the data.")
print(f"  -> answered by {r.provider}")

session.add_tool_result("process_db.query", "pour_temp dropped to 690C between 02:00-04:00")
print("TOOL : process_db.query result saved")

print("\n*** OpenAI quota finished (402) ***\n")
openai.fail_status = 402

print("USER : So what is the root cause?")
r = session.send("So what is the root cause?")
print(f"  -> answered by {r.provider}   failovers={r.failovers}")

print("\nWhat Claude received:")
for m in claude.last_request.messages:
    print(f"  [{m.role}] {m.content[:80]!r}")
print("\nStored history:", [(t.role, t.provider) for t in session.history()])

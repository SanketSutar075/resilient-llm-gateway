"""Step 7: rebuild a clean message list for WHICHEVER provider answers next.
Different providers have different rules (Claude: system is separate, must start with a user message),
so we normalise here once instead of inside the router."""
from gateway.schemas import Message
from state.models import Turn


def to_messages(turns: list[Turn], system_prompt: str | None = None, max_turns: int = 40) -> list[Message]:
    turns = turns[-max_turns:]  # cap history so a long task does not blow the token budget of a smaller model
    msgs: list[Message] = []
    if system_prompt:
        msgs.append(Message(role="system", content=system_prompt))

    for t in turns:
        if t.role == "tool":
            # Tool results are carried as plain text, so ANY provider can read them after a switch.
            role, text = "user", f"[Tool result: {t.tool_name}]\n{t.content}"
        else:
            role, text = t.role, t.content
        if msgs and msgs[-1].role == role and role != "system":
            msgs[-1] = Message(role=role, content=msgs[-1].content + "\n\n" + text)  # merge same-role neighbours
        else:
            msgs.append(Message(role=role, content=text))

    # after trimming, the first non-system message must be a user message
    i = next((i for i, m in enumerate(msgs) if m.role != "system"), None)
    while i is not None and i < len(msgs) and msgs[i].role == "assistant":
        del msgs[i]
    return msgs

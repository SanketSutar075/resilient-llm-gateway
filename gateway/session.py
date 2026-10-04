"""Step 7: ChatSession = Router + Store. The task survives provider switches AND process restarts."""
from gateway.router import Router
from gateway.schemas import ChatRequest, ChatResponse
from state.handoff import to_messages
from state.models import Turn


class ChatSession:
    def __init__(self, router: Router, store, session_id: str,
                 system_prompt: str | None = None, max_turns: int = 40):
        self.router, self.store, self.session_id = router, store, session_id
        self.system_prompt, self.max_turns = system_prompt, max_turns

    def history(self) -> list[Turn]:
        return self.store.load(self.session_id)

    def send(self, text: str) -> ChatResponse:
        # Save the user turn FIRST. If every provider is down, nothing is lost: call resume() later.
        self.store.append(self.session_id, Turn(role="user", content=text))
        return self._generate()

    def add_tool_result(self, tool_name: str, content: str) -> None:
        self.store.append(self.session_id, Turn(role="tool", tool_name=tool_name, content=content))

    def resume(self) -> ChatResponse:
        """Retry the last unanswered turn (e.g. after all providers were down) without duplicating it."""
        turns = self.history()
        if not turns or turns[-1].role == "assistant":
            raise ValueError("Nothing to resume: last turn is already answered")
        return self._generate()

    def _generate(self) -> ChatResponse:
        msgs = to_messages(self.history(), self.system_prompt, self.max_turns)
        resp = self.router.generate(ChatRequest(messages=msgs))
        self.store.append(self.session_id, Turn(role="assistant", content=resp.text, provider=resp.provider))
        return resp

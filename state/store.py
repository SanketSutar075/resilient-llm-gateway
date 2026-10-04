"""Step 7: where history is saved. InMemoryStore for tests/dev, RedisStore for real handoff across restarts."""
from state.models import Turn


class InMemoryStore:
    def __init__(self):
        self._d: dict[str, list[Turn]] = {}

    def append(self, session_id: str, turn: Turn) -> None:
        self._d.setdefault(session_id, []).append(turn)

    def load(self, session_id: str) -> list[Turn]:
        return list(self._d.get(session_id, []))

    def clear(self, session_id: str) -> None:
        self._d.pop(session_id, None)


class RedisStore:
    """History is a Redis list, one JSON turn per item. Expires after ttl_s of inactivity."""

    def __init__(self, url: str = "redis://localhost:6379/0", ttl_s: int = 86400, client=None):
        if client is None:
            import redis  # lazy import: only needed when you really use Redis
            client = redis.Redis.from_url(url, decode_responses=True)
        self.r = client
        self.ttl_s = ttl_s

    @staticmethod
    def _key(session_id: str) -> str:
        return f"chat:{session_id}"

    def append(self, session_id: str, turn: Turn) -> None:
        k = self._key(session_id)
        self.r.rpush(k, turn.model_dump_json())
        self.r.expire(k, self.ttl_s)

    def load(self, session_id: str) -> list[Turn]:
        return [Turn.model_validate_json(x) for x in self.r.lrange(self._key(session_id), 0, -1)]

    def clear(self, session_id: str) -> None:
        self.r.delete(self._key(session_id))

"""Step 5: circuit breaker. Stops sending traffic to a provider that keeps failing.

CLOSED    -> normal, requests allowed
OPEN      -> blocked until cooldown ends
HALF_OPEN -> cooldown ended, allow ONE probe request: success -> CLOSED, failure -> OPEN again
"""
import time
from enum import Enum
from typing import Callable


class State(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, cooldown_s: float = 300,
                 clock: Callable[[], float] = time.monotonic):
        self.failure_threshold = failure_threshold
        self.default_cooldown_s = cooldown_s
        self.clock = clock  # injectable so tests do not need real sleeping
        self.failures = 0
        self.opened_at = 0.0
        self.cooldown_s = cooldown_s
        self._state = State.CLOSED
        self._probe_in_flight = False

    @property
    def state(self) -> State:
        if self._state == State.OPEN and self.clock() - self.opened_at >= self.cooldown_s:
            self._state = State.HALF_OPEN
            self._probe_in_flight = False
        return self._state

    def allow(self) -> bool:
        st = self.state
        if st == State.CLOSED:
            return True
        if st == State.HALF_OPEN and not self._probe_in_flight:
            self._probe_in_flight = True  # only one probe at a time
            return True
        return False

    def record_success(self):
        self.failures = 0
        self._state = State.CLOSED
        self._probe_in_flight = False

    def record_failure(self, cooldown_s: float | None = None, trip_now: bool = False):
        """trip_now=True opens immediately (e.g. quota over). Otherwise opens after N failures."""
        self.failures += 1
        if self._state == State.HALF_OPEN or trip_now or self.failures >= self.failure_threshold:
            self._open(cooldown_s)

    def _open(self, cooldown_s: float | None):
        self._state = State.OPEN
        self.opened_at = self.clock()
        self.cooldown_s = cooldown_s if cooldown_s is not None else self.default_cooldown_s
        self._probe_in_flight = False

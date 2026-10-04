"""Step 4: decide what to DO for each error (retry, switch, or stop)."""
from dataclasses import dataclass
from enum import Enum
from gateway.errors import ProviderError


class Action(str, Enum):
    RETRY_THEN_SWITCH = "retry_then_switch"  # temporary problem: try again with backoff, then move on
    SWITCH = "switch"                        # provider problem: move to next provider now
    FAIL = "fail"                            # our own bug: do not hide it by switching


@dataclass(frozen=True)
class Decision:
    action: Action
    cooldown_s: float  # how long the breaker keeps this provider blocked after the final failure
    reason: str


def classify(err: ProviderError) -> Decision:
    s = err.status
    if s == 400:
        return Decision(Action.FAIL, 0, "bad request (our bug)")
    if s == 429:
        return Decision(Action.RETRY_THEN_SWITCH, 60, "rate limited")
    if s in (401, 402, 403):
        # invalid key / quota over / billing: retrying will never help, block for long
        return Decision(Action.SWITCH, 3600, "auth/quota/billing problem")
    if s is None:
        return Decision(Action.RETRY_THEN_SWITCH, 30, "timeout/connection error")
    if s >= 500:
        return Decision(Action.SWITCH, 30, "provider outage")
    return Decision(Action.SWITCH, 30, f"unexpected status {s}")

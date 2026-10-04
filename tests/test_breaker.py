from gateway.circuit_breaker import CircuitBreaker, State


class Clock:
    def __init__(self): self.t = 0.0
    def __call__(self): return self.t


def test_opens_after_threshold_and_blocks():
    c = Clock(); b = CircuitBreaker(failure_threshold=3, cooldown_s=300, clock=c)
    for _ in range(2):
        b.record_failure()
    assert b.state == State.CLOSED and b.allow()
    b.record_failure()
    assert b.state == State.OPEN and not b.allow()


def test_half_open_after_cooldown_allows_single_probe():
    c = Clock(); b = CircuitBreaker(failure_threshold=1, cooldown_s=300, clock=c)
    b.record_failure()
    c.t = 299; assert not b.allow()
    c.t = 301
    assert b.state == State.HALF_OPEN
    assert b.allow() and not b.allow()  # only one probe at a time


def test_probe_success_closes_probe_failure_reopens():
    c = Clock(); b = CircuitBreaker(failure_threshold=1, cooldown_s=300, clock=c)
    b.record_failure(); c.t = 301; assert b.allow()
    b.record_success(); assert b.state == State.CLOSED
    b.record_failure(); c.t = 700; assert b.allow()
    b.record_failure(); assert b.state == State.OPEN


def test_trip_now_uses_custom_cooldown():
    c = Clock(); b = CircuitBreaker(failure_threshold=5, clock=c)
    b.record_failure(cooldown_s=3600, trip_now=True)
    assert b.state == State.OPEN
    c.t = 3599; assert not b.allow()
    c.t = 3601; assert b.allow()

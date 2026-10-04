"""Router with smart failover (steps 3 to 5).
Flow per provider: breaker allows? -> call -> on error classify -> retry w/ backoff, or switch, or fail."""
import logging
import time
from typing import Callable
from gateway.circuit_breaker import CircuitBreaker, State
from gateway.error_classifier import Action, classify
from gateway.errors import AllProvidersFailed, ProviderError
from gateway.providers.base import BaseProvider
from gateway.schemas import ChatRequest, ChatResponse

log = logging.getLogger("gateway.router")


class Router:
    def __init__(self, providers: list[BaseProvider], max_retries: int = 2,
                 backoff_base_s: float = 0.5, failure_threshold: int = 3,
                 sleep: Callable[[float], None] = time.sleep,
                 clock: Callable[[], float] = time.monotonic):
        self.providers = providers  # priority order: first = preferred
        self.max_retries = max_retries
        self.backoff_base_s = backoff_base_s
        self.sleep = sleep
        self.breakers = {p.name: CircuitBreaker(failure_threshold=failure_threshold, clock=clock)
                         for p in providers}

    def health(self) -> dict[str, str]:
        """Used by the /health endpoint and dashboard later."""
        return {name: b.state.value for name, b in self.breakers.items()}

    def generate(self, req: ChatRequest) -> ChatResponse:
        errors: list[ProviderError] = []
        skipped: list[str] = []
        for p in self.providers:
            breaker = self.breakers[p.name]
            if not breaker.allow():
                log.info("Skipping %s (circuit %s)", p.name, breaker.state.value)
                skipped.append(p.name)
                continue
            try:
                resp = self._call_with_retry(p, breaker, req)
                resp.failovers = [e.provider for e in errors]
                resp.skipped = skipped
                if errors or skipped:
                    log.warning("Answered by %s | failed=%s skipped=%s", p.name, resp.failovers, skipped)
                return resp
            except ProviderError as e:
                if classify(e).action == Action.FAIL:
                    raise  # our own bug, switching would hide it
                errors.append(e)
        raise AllProvidersFailed(errors)

    def _call_with_retry(self, p: BaseProvider, breaker: CircuitBreaker, req: ChatRequest) -> ChatResponse:
        attempt = 0
        while True:
            try:
                resp = p.generate(req)
                breaker.record_success()
                return resp
            except ProviderError as e:
                d = classify(e)
                if d.action == Action.FAIL:
                    # not the provider's fault: do not count against the breaker, but release a half-open probe
                    if breaker.state == State.HALF_OPEN:
                        breaker.record_success()
                    raise
                if d.action == Action.RETRY_THEN_SWITCH and attempt < self.max_retries \
                        and breaker.state != State.HALF_OPEN:
                    wait = self.backoff_base_s * (2 ** attempt)
                    log.warning("%s: %s. Retry %d/%d in %.1fs", p.name, d.reason, attempt + 1,
                                self.max_retries, wait)
                    self.sleep(wait)
                    attempt += 1
                    continue
                hard = d.action == Action.SWITCH and d.cooldown_s >= 3600  # quota/auth: block at once
                breaker.record_failure(cooldown_s=d.cooldown_s, trip_now=hard)
                log.warning("%s failed (%s). Switching.", p.name, d.reason)
                raise

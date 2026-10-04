"""Provider errors in ONE common format, so the router never sees SDK-specific exceptions."""


class ProviderError(Exception):
    def __init__(self, provider: str, status: int | None, message: str):
        super().__init__(f"[{provider}] status={status}: {message}")
        self.provider = provider
        self.status = status
        self.message = message

    @property
    def should_failover(self) -> bool:
        # 400 = our own bad request. Switching provider will not fix it.
        if self.status == 400:
            return False
        return True  # 401/402/429/5xx/timeout/None -> try the next provider


class AllProvidersFailed(Exception):
    def __init__(self, errors: list[ProviderError]):
        super().__init__("All providers failed: " + " | ".join(str(e) for e in errors))
        self.errors = errors

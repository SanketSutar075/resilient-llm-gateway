"""Common data format. Every provider adapter converts to/from these."""
from pydantic import BaseModel, Field
from typing import Literal


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    max_tokens: int = 1000
    temperature: float = 0.2


class ChatResponse(BaseModel):
    text: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    # which providers failed before this one answered (useful for the dashboard later)
    failovers: list[str] = Field(default_factory=list)
    # providers skipped because their circuit breaker was open
    skipped: list[str] = Field(default_factory=list)

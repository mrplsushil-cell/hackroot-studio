"""LLM provider abstraction."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable


@dataclass
class LLMMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    content: str
    model: str | None = None
    usage: dict | None = None
    raw: dict | None = None


class LLMProvider(ABC):
    """Abstract base for LLM providers. Implementations: openai, anthropic, mock."""

    name: str = "base"

    @abstractmethod
    async def chat(
        self,
        messages: Iterable[LLMMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        response_format_json: bool = False,
    ) -> LLMResponse: ...

    async def close(self) -> None:  # noqa: D401
        """Optional cleanup."""
        return None

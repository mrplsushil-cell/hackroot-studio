"""LLM provider factory.

Selects an implementation based on settings or an explicit name. New providers
(e.g. Anthropic, Google) only need a new module + an entry in `_PROVIDERS`.
"""
from __future__ import annotations
from functools import lru_cache

from app.config import settings
from app.providers.base import ProviderError
from app.providers.llm.base import LLMProvider
from app.providers.llm.mock import MockLLMProvider
from app.providers.llm.openai_provider import OpenAILLMProvider


_PROVIDERS: dict[str, type[LLMProvider]] = {
    "mock": MockLLMProvider,
    "openai": OpenAILLMProvider,
    # Add new providers here:
    # "anthropic": AnthropicLLMProvider,
    # "google": GoogleLLMProvider,
}


def make_llm_provider(name: str | None = None) -> LLMProvider:
    name = (name or settings.llm_provider or "mock").lower()
    cls = _PROVIDERS.get(name)
    if cls is None:
        raise ProviderError(f"Unknown LLM provider: {name!r}. "
                            f"Available: {sorted(_PROVIDERS)}")
    return cls()

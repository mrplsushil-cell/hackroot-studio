"""TTS provider factory."""
from __future__ import annotations

from app.config import settings
from app.providers.base import ProviderError
from app.providers.tts.base import TTSProvider
from app.providers.tts.mock import MockTTSProvider
from app.providers.tts.openai_provider import OpenAITTSProvider

_PROVIDERS: dict[str, type[TTSProvider]] = {
    "mock": MockTTSProvider,
    "openai": OpenAITTSProvider,
}


def make_tts_provider(name: str | None = None) -> TTSProvider:
    name = (name or settings.tts_provider or "mock").lower()
    cls = _PROVIDERS.get(name)
    if cls is None:
        raise ProviderError(f"Unknown TTS provider: {name!r}. Available: {sorted(_PROVIDERS)}")
    return cls()

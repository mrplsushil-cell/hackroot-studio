"""Image provider factory."""
from __future__ import annotations

from app.config import settings
from app.providers.base import ProviderError
from app.providers.image.base import ImageProvider
from app.providers.image.mock import MockImageProvider
from app.providers.image.openai_provider import OpenAIImageProvider

_PROVIDERS: dict[str, type[ImageProvider]] = {
    "mock": MockImageProvider,
    "openai": OpenAIImageProvider,
}


def make_image_provider(name: str | None = None) -> ImageProvider:
    name = (name or settings.image_provider or "mock").lower()
    cls = _PROVIDERS.get(name)
    if cls is None:
        raise ProviderError(f"Unknown image provider: {name!r}. Available: {sorted(_PROVIDERS)}")
    return cls()

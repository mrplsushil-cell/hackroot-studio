"""Music provider factory."""
from __future__ import annotations

from app.config import settings
from app.providers.base import ProviderError
from app.providers.music.base import MusicProvider
from app.providers.music.mock import MockMusicProvider

_PROVIDERS: dict[str, type[MusicProvider]] = {
    "mock": MockMusicProvider,
}


def make_music_provider(name: str | None = None) -> MusicProvider:
    name = (name or settings.music_provider or "mock").lower()
    cls = _PROVIDERS.get(name)
    if cls is None:
        raise ProviderError(f"Unknown music provider: {name!r}. Available: {sorted(_PROVIDERS)}")
    return cls()

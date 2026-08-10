"""Video provider factory."""
from __future__ import annotations

from app.config import settings
from app.providers.base import ProviderError
from app.providers.video.base import VideoProvider
from app.providers.video.mock import MockVideoProvider

_PROVIDERS: dict[str, type[VideoProvider]] = {
    "mock": MockVideoProvider,
    # Real providers go here. Each is a stub until implemented:
    # "runway": RunwayVideoProvider,
    # "luma": LumaVideoProvider,
    # "replicate": ReplicateVideoProvider,
}


def make_video_provider(name: str | None = None) -> VideoProvider:
    name = (name or settings.video_provider or "mock").lower()
    cls = _PROVIDERS.get(name)
    if cls is None:
        raise ProviderError(f"Unknown video provider: {name!r}. Available: {sorted(_PROVIDERS)}")
    return cls()

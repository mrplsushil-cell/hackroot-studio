"""Mock video provider — returns None to signal that the pipeline should fall
back to local image-based assembly (FFmpeg + Ken Burns)."""
from __future__ import annotations

from app.providers.video.base import VideoProvider, VideoRequest, VideoResult


class MockVideoProvider(VideoProvider):
    name = "mock"

    async def generate(self, request: VideoRequest, *, out_path: str) -> VideoResult | None:
        return None

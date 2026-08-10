"""Video provider abstraction."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class VideoRequest:
    prompt: str
    duration: int = 4
    aspect_ratio: str = "9:16"
    image_path: str | None = None  # for image-to-video
    seed: int | None = None


@dataclass
class VideoResult:
    path: str
    duration: float
    width: int
    height: int
    provider: str
    model: str | None = None


class VideoProvider(ABC):
    """Generate a short video clip from a prompt or image.

    The mock provider is a no-op (returns None) because Hackroot's pipeline
    always assembles the final video locally via FFmpeg with Ken Burns effects
    on the generated stills. Real providers can be plugged in here for
    image-to-video (Runway, Luma, Stability, Replicate).
    """

    name: str = "base"

    @abstractmethod
    async def generate(self, request: VideoRequest, *, out_path: str) -> VideoResult | None: ...

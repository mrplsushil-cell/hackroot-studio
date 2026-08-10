"""Image provider abstraction."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ImageRequest:
    prompt: str
    negative_prompt: str | None = None
    width: int = 1024
    height: int = 1024
    seed: int | None = None
    reference_image_path: str | None = None  # for image-to-image
    style: str | None = None
    brand_hint: str | None = None


@dataclass
class ImageResult:
    path: str  # local path on disk
    width: int
    height: int
    provider: str
    model: str | None = None
    seed: int | None = None


class ImageProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def generate(self, request: ImageRequest, *, out_path: str) -> ImageResult: ...

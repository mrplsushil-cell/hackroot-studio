"""Music provider abstraction."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class MusicRequest:
    prompt: str
    duration: float
    style: str = "Cinematic"
    intensity: str = "med"  # low | med | high
    seed: int | None = None


@dataclass
class MusicResult:
    path: str
    duration: float
    provider: str
    model: str | None = None


class MusicProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def generate(self, request: MusicRequest, *, out_path: str) -> MusicResult | None: ...

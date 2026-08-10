"""TTS provider abstraction."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class TTSRequest:
    text: str
    voice: str = "female"           # male | female
    language: str = "English"       # English | Hindi | Hinglish | Punjabi
    speed: float = 1.0
    style: str | None = None


@dataclass
class TTSResult:
    path: str
    duration: float
    provider: str
    model: str | None = None


class TTSProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def synthesize(self, request: TTSRequest, *, out_path: str) -> TTSResult: ...

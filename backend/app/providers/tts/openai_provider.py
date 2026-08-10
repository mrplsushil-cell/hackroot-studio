"""OpenAI TTS provider."""
from __future__ import annotations
import os
import wave
from pathlib import Path

import httpx

from app.config import settings
from app.providers.base import ProviderError
from app.providers.tts.base import TTSProvider, TTSRequest, TTSResult

_VOICE_MAP = {
    "male": "onyx",
    "female": "nova",
}


class OpenAITTSProvider(TTSProvider):
    name = "openai"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.tts_api_key
        if not self.api_key:
            raise ProviderError("OpenAI TTS requires TTS_API_KEY.")
        self._client = httpx.AsyncClient(timeout=60.0)

    async def synthesize(self, request: TTSRequest, *, out_path: str) -> TTSResult:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        voice = _VOICE_MAP.get(request.voice, "nova")
        body = {"model": "tts-1", "voice": voice, "input": request.text,
                "response_format": "wav"}
        r = await self._client.post(
            "https://api.openai.com/v1/audio/speech",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=body,
        )
        if r.status_code != 200:
            raise ProviderError(f"OpenAI TTS error {r.status_code}: {r.text[:200]}")
        Path(out_path).write_bytes(r.content)
        # Duration
        try:
            with wave.open(out_path, "rb") as w:
                duration = w.getnframes() / float(w.getframerate())
        except Exception:
            duration = 0.0
        return TTSResult(path=out_path, duration=duration, provider=self.name, model="tts-1")

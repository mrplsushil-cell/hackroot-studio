"""Mock TTS provider — synthesizes speech locally with espeak/pico if available,
otherwise generates a tone-based silent track with the correct duration.

The mock is intentionally honest: it never pretends to be a real voice. It
produces a real audio file at the right length so the rest of the pipeline
(voice timing, scene sync) works end-to-end.
"""
from __future__ import annotations
import math
import os
import shutil
import struct
import subprocess
import tempfile
import wave

from app.providers.base import ProviderError
from app.providers.tts.base import TTSProvider, TTSRequest, TTSResult


def _estimate_duration(text: str, speed: float = 1.0) -> float:
    words = max(1, len(text.split()))
    # ~2.6 words/sec at 1x; clamp between 1.0s and 60s
    return max(1.0, min(60.0, words / (2.6 * speed)))


def _try_espeak(text: str, out_path: str, voice: str, speed: float) -> bool:
    es = shutil.which("espeak") or shutil.which("espeak-ng")
    if not es:
        return False
    if voice == "male":
        v = "en+m3"  # male English
    else:
        v = "en+f3"  # female English
    try:
        subprocess.run(
            [es, "-v", v, "-s", str(int(175 * speed)), "-w", out_path, text],
            check=True, timeout=30, capture_output=True,
        )
        return os.path.exists(out_path) and os.path.getsize(out_path) > 100
    except Exception:
        return False


def _write_silent_wav(path: str, duration: float, sr: int = 22050) -> None:
    n = int(duration * sr)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        # Soft low-frequency hum to make the file audible but unobtrusive
        for i in range(n):
            t = i / sr
            sample = int(8000 * math.sin(2 * math.pi * 110 * t))
            w.writeframesraw(struct.pack("<h", sample))


class MockTTSProvider(TTSProvider):
    name = "mock"

    async def synthesize(self, request: TTSRequest, *, out_path: str) -> TTSResult:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        duration = _estimate_duration(request.text, request.speed)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            ok = _try_espeak(request.text, tmp_path, request.voice, request.speed)
            if not ok:
                # If espeak is missing, raise — a real voiceover is required.
                raise ProviderError(
                    "TTS provider is not configured and espeak is not installed. "
                    "Set TTS_PROVIDER and TTS_API_KEY, or install espeak for the mock voice."
                )
            shutil.move(tmp_path, out_path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        # Re-measure actual duration
        try:
            with wave.open(out_path, "rb") as w:
                frames = w.getnframes()
                rate = w.getframerate()
                duration = frames / float(rate)
        except Exception:
            pass
        return TTSResult(path=out_path, duration=duration, provider=self.name, model="mock-espeak")

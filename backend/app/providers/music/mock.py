"""Mock music provider — generates a stylistically appropriate ambient track
locally using additive synthesis so the final video has a real background bed
that matches the requested style/intensity without any external API.

Tracks are short, royalty-free, generated on the fly. The output is a real WAV
file at the requested duration.
"""
from __future__ import annotations
import math
import os
import struct
import wave

from app.providers.music.base import MusicProvider, MusicRequest, MusicResult


_STYLE_PROFILES: dict[str, dict] = {
    "cinematic":         {"base_hz": 110.0, "harmonics": [1.0, 0.5, 0.3, 0.18], "lfo": 0.12, "tempo": 60},
    "product advertisement": {"base_hz": 220.0, "harmonics": [1.0, 0.4, 0.6, 0.2], "lfo": 0.4, "tempo": 110},
    "social media reel": {"base_hz": 196.0, "harmonics": [1.0, 0.55, 0.3], "lfo": 0.5, "tempo": 120},
    "corporate":         {"base_hz": 174.6, "harmonics": [1.0, 0.4, 0.25], "lfo": 0.08, "tempo": 90},
    "minimal":           {"base_hz": 130.8, "harmonics": [1.0, 0.2, 0.1], "lfo": 0.05, "tempo": 70},
    "luxury":            {"base_hz": 146.8, "harmonics": [1.0, 0.6, 0.3, 0.15], "lfo": 0.15, "tempo": 80},
    "fashion":           {"base_hz": 261.6, "harmonics": [1.0, 0.45, 0.7], "lfo": 0.35, "tempo": 115},
    "documentary":       {"base_hz": 98.0,  "harmonics": [1.0, 0.5, 0.2, 0.1], "lfo": 0.07, "tempo": 65},
    "storytelling":      {"base_hz": 164.8, "harmonics": [1.0, 0.4, 0.3, 0.15], "lfo": 0.2, "tempo": 75},
}


def _profile_for(style: str) -> dict:
    s = (style or "").strip().lower()
    return _STYLE_PROFILES.get(s, _STYLE_PROFILES["cinematic"])


def _intensity_amp(intensity: str) -> float:
    return {"low": 0.10, "med": 0.18, "high": 0.26}.get(intensity.lower(), 0.18)


class MockMusicProvider(MusicProvider):
    name = "mock"

    async def generate(self, request: MusicRequest, *, out_path: str) -> MusicResult:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        prof = _profile_for(request.style)
        amp = _intensity_amp(request.intensity)
        sr = 22050
        n = int(request.duration * sr)
        base = prof["base_hz"]
        harm = prof["harmonics"]
        lfo_hz = prof["lfo"]
        tempo = prof["tempo"]
        beat_period = 60.0 / tempo

        with wave.open(out_path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sr)
            buf = bytearray()
            for i in range(n):
                t = i / sr
                # Slow LFO swell
                lfo = 0.5 + 0.5 * math.sin(2 * math.pi * lfo_hz * t)
                # Beat envelope (a soft thump every beat)
                phase = (t % beat_period) / beat_period
                beat_env = math.exp(-phase * 6.0)
                sig = 0.0
                for k, a in enumerate(harm, start=1):
                    sig += a * math.sin(2 * math.pi * base * k * t)
                # Pad with a soft fifth
                sig += 0.3 * math.sin(2 * math.pi * base * 1.5 * t)
                sig = sig / (sum(harm) + 0.3)
                # Combine LFO + beat
                sample = sig * (0.5 + 0.5 * lfo) * amp + 0.4 * beat_env * amp
                # Soft clip
                sample = math.tanh(sample * 1.5) * 0.8
                # Fade in/out (1s)
                fade = min(1.0, t / 1.0, (request.duration - t) / 1.0)
                sample *= max(0.0, fade)
                v = int(sample * 32000)
                buf.extend(struct.pack("<h", max(-32768, min(32767, v))))
            w.writeframesraw(bytes(buf))
        return MusicResult(path=out_path, duration=request.duration, provider=self.name,
                           model="mock-synth-v1")

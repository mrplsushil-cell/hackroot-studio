"""Thin wrapper around the system `ffmpeg`/`ffprobe` binaries."""
from __future__ import annotations
import json
import os
import subprocess
from dataclasses import dataclass

from app.config import settings


class FFmpegError(RuntimeError):
    pass


@dataclass
class MediaInfo:
    width: int
    height: int
    duration: float
    has_audio: bool
    fps: float
    codec: str | None = None
    bit_rate: int | None = None


def run(cmd: list[str], *, timeout: int = 600) -> str:
    # Callers legitimately pass Path objects; normalize so both subprocess and
    # the error formatting below can never blow up on a non-str argument.
    cmd = [str(c) for c in cmd]
    try:
        result = subprocess.run(
            cmd, check=True, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise FFmpegError(f"FFmpeg failed: {' '.join(cmd)}\n{(e.stderr or '')[-2000:]}") from e
    except subprocess.TimeoutExpired as e:
        raise FFmpegError(
            f"FFmpeg timed out after {timeout}s: {' '.join(cmd)}"
        ) from e
    except FileNotFoundError as e:
        raise FFmpegError(
            "ffmpeg/ffprobe binary not found. Install ffmpeg and ensure it is on PATH."
        ) from e


def probe(path: str) -> MediaInfo:
    if not os.path.exists(path):
        raise FFmpegError(f"ffprobe: file does not exist: {path}")
    cmd = [
        settings.ffprobe_bin, "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", path,
    ]
    raw = run(cmd)
    data = json.loads(raw)
    streams = data.get("streams", [])
    fmt = data.get("format", {})
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if not v:
        raise FFmpegError(f"No video stream in {path}")
    fps = 30.0
    fr = v.get("avg_frame_rate") or v.get("r_frame_rate") or "30/1"
    try:
        num, den = fr.split("/")
        num, den = float(num), float(den) or 1.0
        if num > 0:
            fps = num / den
    except Exception:
        pass
    return MediaInfo(
        width=int(v.get("width", 0)),
        height=int(v.get("height", 0)),
        duration=float(fmt.get("duration", v.get("duration", 0.0)) or 0.0),
        has_audio=a is not None,
        fps=fps,
        codec=v.get("codec_name"),
        bit_rate=int(fmt["bit_rate"]) if "bit_rate" in fmt else None,
    )


def make_thumbnail(video_path: str, out_path: str, *, at_seconds: float = 1.0) -> str:
    cmd = [
        settings.ffmpeg_bin, "-y", "-ss", f"{at_seconds:.2f}", "-i", video_path,
        "-frames:v", "1", "-q:v", "2", out_path,
    ]
    run(cmd)
    return out_path

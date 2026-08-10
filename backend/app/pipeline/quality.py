"""Quality Control agent — validates the rendered output before delivery.

Checks:
- Output file exists
- Duration within tolerance of requested
- Resolution correct
- Aspect ratio correct
- Thumbnail exists
- File size > 0 and reasonable
"""
from __future__ import annotations
import os
from dataclasses import dataclass, field

from app.utils.ffmpeg import probe


@dataclass
class QCResult:
    ok: bool
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"ok": self.ok, "issues": self.issues, "warnings": self.warnings}


def run_qc(
    *,
    output_path: str,
    expected_duration: int,
    expected_aspect: str,
    thumbnail_path: str | None = None,
    voice_path: str | None = None,
) -> QCResult:
    res = QCResult(ok=True)

    if not output_path or not os.path.exists(output_path):
        res.ok = False
        res.issues.append("Output file does not exist")
        return res

    if os.path.getsize(output_path) < 1024:
        res.ok = False
        res.issues.append("Output file is suspiciously small (<1KB)")

    try:
        info = probe(output_path)
    except Exception as e:
        res.ok = False
        res.issues.append(f"ffprobe failed: {e}")
        return res

    # Duration
    if abs(info.duration - expected_duration) > max(1.5, expected_duration * 0.15):
        res.warnings.append(
            f"Duration {info.duration:.2f}s differs from requested {expected_duration}s"
        )

    # Aspect
    expected = {
        "16:9": (16, 9), "9:16": (9, 16), "1:1": (1, 1), "4:5": (4, 5),
    }.get(expected_aspect, (9, 16))
    actual = (info.width, info.height)
    if actual[0] * expected[1] != actual[1] * expected[0]:
        # tolerate small float rounding
        if abs(actual[0] / actual[1] - expected[0] / expected[1]) > 0.02:
            res.warnings.append(
                f"Aspect ratio mismatch: expected {expected_aspect} got {actual[0]}x{actual[1]}"
            )

    if voice_path and not os.path.exists(voice_path):
        res.warnings.append("Voiceover file missing")

    if thumbnail_path and not os.path.exists(thumbnail_path):
        res.warnings.append("Thumbnail not generated")

    return res

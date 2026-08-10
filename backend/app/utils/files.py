"""Filesystem helpers for the pipeline (work dirs, paths, MIME detection)."""
from __future__ import annotations
import os
import re
import tempfile
from pathlib import Path
from typing import Iterable


_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")
_DOT_RUN = re.compile(r"\.{2,}")


def safe_filename(name: str) -> str:
    """Sanitize a user-supplied filename stem into a safe, traversal-proof token."""
    name = os.path.basename(name.strip().replace("\\", "/"))
    name = name.replace(" ", "_")
    name = _SAFE_NAME.sub("_", name)
    name = _DOT_RUN.sub("_", name)          # kill ".." traversal sequences
    name = name.strip("._-")                # no leading/trailing dots or separators
    return name[:120] or "file"


def ensure_dir(path: str | os.PathLike) -> str:
    Path(path).mkdir(parents=True, exist_ok=True)
    return str(path)


def video_workdir(root: str, video_id: int) -> str:
    p = Path(root) / f"video_{video_id}"
    p.mkdir(parents=True, exist_ok=True)
    for sub in ("scenes", "images", "voice", "music", "captions", "clips", "thumbs", "logs"):
        (p / sub).mkdir(exist_ok=True)
    return str(p)


def aspect_to_size(aspect: str, base: int = 1024) -> tuple[int, int]:
    a = (aspect or "9:16").strip()
    if a in ("16:9",):
        return (1280, 720) if base == 1024 else (1920, 1080)
    if a in ("9:16",):
        return (720, 1280) if base == 1024 else (1080, 1920)
    if a in ("1:1",):
        return (base, base)
    if a in ("4:5",):
        return (base, int(base * 5 / 4))
    return (720, 1280)


def list_files(*roots: str, exts: Iterable[str] | None = None) -> list[str]:
    exts_set = {e.lower().lstrip(".") for e in (exts or [])}
    out: list[str] = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, _, files in os.walk(root):
            for f in files:
                if exts_set and Path(f).suffix.lower().lstrip(".") not in exts_set:
                    continue
                out.append(os.path.join(dirpath, f))
    return out


def tempdir(suffix: str = "") -> str:
    return tempfile.mkdtemp(suffix=suffix)

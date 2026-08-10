"""Tests for product image mode in the AI pipeline."""
from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from app.pipeline.director import VideoDirector, VideoDirectorError


def write_image(path: Path, size: tuple[int, int]) -> Path:
    Image.new("RGB", size, (220, 40, 90)).save(path, format="PNG")
    return path


def test_product_image_fits_canvas_without_distortion(tmp_path: Path):
    """A wide source must be letterboxed into a tall canvas, never stretched."""
    src = write_image(tmp_path / "wide.png", (400, 100))
    dest = tmp_path / "scene_01.png"

    out = VideoDirector._place_product_image(str(src), str(dest), (720, 1280))

    assert Path(out).exists()
    with Image.open(out) as im:
        assert im.size == (720, 1280), "output must match the render canvas exactly"

    # Original upload must be untouched.
    with Image.open(src) as orig:
        assert orig.size == (400, 100)


def test_product_image_preserves_source_file(tmp_path: Path):
    src = write_image(tmp_path / "orig.png", (200, 200))
    before = src.read_bytes()
    VideoDirector._place_product_image(str(src), str(tmp_path / "o.png"), (512, 512))
    assert src.read_bytes() == before, "the user's upload must never be modified"


def test_product_image_handles_square_and_tall_sources(tmp_path: Path):
    for name, size in [("sq.png", (300, 300)), ("tall.png", (100, 500))]:
        src = write_image(tmp_path / name, size)
        dest = tmp_path / f"out_{name}"
        VideoDirector._place_product_image(str(src), str(dest), (1080, 1920))
        with Image.open(dest) as im:
            assert im.size == (1080, 1920)


def test_missing_product_image_raises_pipeline_error(tmp_path: Path):
    with pytest.raises(VideoDirectorError) as e:
        VideoDirector._place_product_image(
            str(tmp_path / "nope.png"), str(tmp_path / "o.png"), (720, 1280)
        )
    assert e.value.step == "assets"

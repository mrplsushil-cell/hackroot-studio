"""Regression tests for the FFmpeg filtergraph builders.

These guard the bugs found during end-to-end rendering:
  * `force_aspect_ratio` is not a real FFmpeg option (it is
    `force_original_aspect_ratio`) — using it aborted the xfade concat.
  * The audio filterchains must be joined with ';' or FFmpeg reports
    "Trailing garbage after a filter".
  * `zoompan` made a 5s clip take ~114s; the crop-based Ken Burns must not
    reintroduce it.
"""
from __future__ import annotations

import inspect

from app.rendering import renderer as R


def test_kb_filter_has_no_zoompan():
    """zoompan is ~16x slower than realtime here; keep it out of the graph."""
    f = R._kb_filter(5.0, 720, 1280, 1.0, 1.15, 0.0, 0.0)
    assert "zoompan" not in f
    assert f.endswith("fps=30")


def test_kb_filter_emits_even_dimensions():
    """yuv420p requires even width/height or libx264 refuses to open."""
    import re

    f = R._kb_filter(3.0, 720, 1280, 1.0, 1.2, 0.0, 0.0)
    for w, h in re.findall(r"(?:scale|crop)=(\d+):(\d+)", f):
        assert int(w) % 2 == 0 and int(h) % 2 == 0, f"odd dimension in {f}"


def test_kb_filter_scales_to_requested_output():
    f = R._kb_filter(4.0, 1080, 1920, 1.0, 1.1, 0.0, 0.0)
    assert "scale=1080:1920" in f
    assert "setsar=1" in f


def test_kb_filter_pan_directions_differ():
    """A positive and negative pan bias must produce different expressions."""
    fwd = R._kb_filter(4.0, 720, 1280, 1.0, 1.1, 1.0, 0.0)
    back = R._kb_filter(4.0, 720, 1280, 1.0, 1.1, -1.0, 0.0)
    still = R._kb_filter(4.0, 720, 1280, 1.0, 1.1, 0.0, 0.0)
    assert fwd != back != still


def test_no_invalid_force_aspect_ratio_option():
    """`force_aspect_ratio` silently kills the render; only the
    `force_original_aspect_ratio` spelling is valid."""
    src = inspect.getsource(R)
    for line in src.splitlines():
        if "force_aspect_ratio" in line:
            assert "force_original_aspect_ratio" in line, line.strip()


def test_audio_filterchains_are_semicolon_separated():
    """Reproduces the 'Trailing garbage after a filter' mux failure."""
    src = inspect.getsource(R)
    assert "';'.join(amix_inputs)" in src, "amix chains must be ';'-joined"
    assert "''.join(amix_inputs)" not in src

"""Mock image provider — produces deterministic, attractive gradient+pattern images.

Used for development, tests, and as a fallback when no IMAGE_API_KEY is set.
Crucially, it is real PNG/JPEG output generated locally — NOT a placeholder.
"""
from __future__ import annotations
import hashlib
import math
import os
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from app.providers.image.base import ImageProvider, ImageRequest, ImageResult

_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


def _find_font(size: int) -> ImageFont.ImageFont:
    for p in _FONT_CANDIDATES:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _color_palette(seed: int) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
    rng = random.Random(seed)
    palettes = [
        ((255, 94, 77), (255, 195, 0), (28, 37, 64)),    # warm
        ((106, 17, 203), (37, 117, 252), (242, 242, 247)),
        ((255, 142, 83), (255, 213, 145), (44, 19, 56)),
        ((46, 196, 182), (231, 29, 54), (10, 23, 78)),
        ((255, 211, 105), (255, 117, 117), (38, 70, 83)),
        ((131, 56, 236), (255, 0, 110), (3, 7, 30)),
    ]
    return rng.choice(palettes)


def _draw_gradient(img: Image.Image, c1: tuple[int, int, int], c2: tuple[int, int, int]) -> None:
    w, h = img.size
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(h - 1, 1)
        r = int(c1[0] * (1 - t) + c2[0] * t)
        g = int(c1[1] * (1 - t) + c2[1] * t)
        b = int(c1[2] * (1 - t) + c2[2] * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))


def _draw_orb(img: Image.Image, cx: int, cy: int, r: int, color: tuple[int, int, int]) -> None:
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i in range(r, 0, -1):
        alpha = int(180 * (1 - i / r) ** 2)
        d.ellipse((cx - i, cy - i, cx + i, cy + i), fill=color + (alpha,))
    layer = layer.filter(ImageFilter.GaussianBlur(radius=r * 0.18))
    img.paste(layer, (0, 0), layer)


def _draw_grid(img: Image.Image, color: tuple[int, int, int]) -> None:
    w, h = img.size
    step = max(40, min(w, h) // 14)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for x in range(0, w, step):
        d.line([(x, 0), (x, h)], fill=color + (32,))
    for y in range(0, h, step):
        d.line([(0, y), (w, y)], fill=color + (32,))
    img.paste(overlay, (0, 0), overlay)


def _wrap(text: str, max_chars: int) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + 1 + len(w) > max_chars and cur:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines[:4]


class MockImageProvider(ImageProvider):
    name = "mock"

    async def generate(self, request: ImageRequest, *, out_path: str) -> ImageResult:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        seed = int(request.seed) if request.seed is not None else int(
            hashlib.sha256(request.prompt.encode("utf-8")).hexdigest()[:8], 16
        )
        rng = random.Random(seed)
        c1, c2, c3 = _color_palette(seed)
        w, h = request.width, request.height
        img = Image.new("RGB", (w, h), c1)
        _draw_gradient(img, c1, c2)
        _draw_orb(img, int(w * rng.uniform(0.25, 0.75)), int(h * rng.uniform(0.25, 0.65)),
                  int(min(w, h) * 0.42), c3)
        if rng.random() < 0.6:
            _draw_grid(img, c3)
        # Highlight text from the prompt (so the visual is recognizable)
        words = request.prompt.split()
        # Take a meaningful snippet: first 3 content words
        snippet_words = [w.strip(",.:;\"'()[]") for w in words if len(w) > 3][:5]
        snippet = " ".join(snippet_words) if snippet_words else "Hackroot Studio"
        snippet = snippet[:40]
        font = _find_font(max(28, min(w, h) // 14))
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay)
        lines = _wrap(snippet, 22)
        line_h = font.size + 8
        block_h = line_h * len(lines)
        y = h - block_h - max(40, h // 12)
        for line in lines:
            bbox = d.textbbox((0, 0), line, font=font)
            tw = bbox[2] - bbox[0]
            x = (w - tw) // 2
            # soft shadow
            d.text((x + 4, y + 4), line, font=font, fill=(0, 0, 0, 180))
            d.text((x, y), line, font=font, fill=(255, 255, 255, 245))
            y += line_h
        overlay = overlay.filter(ImageFilter.GaussianBlur(radius=0.6))
        img.paste(overlay, (0, 0), overlay)

        # Top-left accent
        d2 = ImageDraw.Draw(img)
        d2.rectangle([(0, 0), (max(6, w // 80), h)], fill=c3)

        fmt = "PNG" if out_path.lower().endswith(".png") else "JPEG"
        img.save(out_path, fmt, quality=92)
        return ImageResult(path=out_path, width=w, height=h, provider=self.name,
                           model="mock-grad-v1", seed=seed)

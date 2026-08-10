"""OpenAI DALL·E image provider."""
from __future__ import annotations
import base64
import os
from pathlib import Path

import httpx

from app.config import settings
from app.providers.base import ProviderError
from app.providers.image.base import ImageProvider, ImageRequest, ImageResult


class OpenAIImageProvider(ImageProvider):
    name = "openai"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or settings.image_api_key
        self.model = model or settings.image_model or "dall-e-3"
        if not self.api_key:
            raise ProviderError("OpenAI image provider requires IMAGE_API_KEY (OPENAI_API_KEY).")
        self._client = httpx.AsyncClient(timeout=120.0)

    async def generate(self, request: ImageRequest, *, out_path: str) -> ImageResult:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        body = {
            "model": self.model,
            "prompt": request.prompt[:1000],
            "n": 1,
            "size": f"{request.width}x{request.height}",
            "response_format": "b64_json",
        }
        r = await self._client.post(
            "https://api.openai.com/v1/images/generations",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=body,
        )
        if r.status_code != 200:
            raise ProviderError(f"OpenAI image error {r.status_code}: {r.text[:200]}")
        data = r.json()
        b64 = data["data"][0]["b64_json"]
        Path(out_path).write_bytes(base64.b64decode(b64))
        return ImageResult(path=out_path, width=request.width, height=request.height,
                           provider=self.name, model=self.model)

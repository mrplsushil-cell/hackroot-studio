"""Provider base types and registry helpers."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any


class ProviderError(RuntimeError):
    """Raised when a provider cannot complete a request.

    The frontend shows a friendly error based on `.user_message`; the original
    exception is preserved for logs.
    """

    def __init__(self, user_message: str, *args: Any) -> None:
        super().__init__(user_message, *args)
        self.user_message = user_message


@dataclass
class GenerationContext:
    user_id: int
    video_id: int
    job_id: int
    brand_kit: dict | None = None
    style: str = "Cinematic"
    language: str = "English"

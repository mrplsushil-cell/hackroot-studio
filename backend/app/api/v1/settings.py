"""Read-only application settings for the client Settings page.

Exposes only client-safe configuration (rendering defaults, storage backend,
provider availability). Secrets are never returned.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.config import settings
from app.services import email_events

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
async def get_settings() -> dict:
    return {
        "storage": {
            "backend": settings.storage_backend,
            "local_root": settings.storage_local_root,
            "public_base_url": settings.storage_public_base_url,
            "max_upload_size_mb": settings.max_upload_size_mb,
        },
        "rendering": {
            "ffmpeg_bin": settings.ffmpeg_bin,
            "ffprobe_bin": settings.ffprobe_bin,
            "video_preset": settings.video_preset,
            "video_crf": settings.video_crf,
            "audio_codec": settings.audio_codec,
            "audio_bitrate": settings.audio_bitrate,
        },
        "auth": {
            "jwt_algorithm": settings.jwt_algorithm,
            "jwt_expires_minutes": settings.jwt_expires_minutes,
        },
        # Provider configuration status — surfaced to the UI/admin so missing
        # credentials show as a status, never as a silent failure. No secrets.
        "providers": {
            "llm": settings.llm_provider,
            "image": settings.image_provider,
            "video": settings.video_provider,
            "music": settings.music_provider,
            "tts": settings.tts_provider,
            "payments": "razorpay" if settings.razorpay_key_id else "mock",
            "email": email_events.provider_status(),
        },
    }

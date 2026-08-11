"""Application configuration loaded from environment."""
from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Core
    app_name: str = "Hackroot Studio"
    app_env: str = "development"
    app_debug: bool = True
    app_secret_key: str = "change-me"
    app_base_url: str = "http://localhost:8000"
    frontend_base_url: str = "http://localhost:3000"

    # Database
    database_url: str = "postgresql+asyncpg://hackroot:hackroot@localhost:5432/hackroot"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Storage
    storage_backend: Literal["local", "s3"] = "local"
    storage_local_root: str = "/data/storage"
    storage_public_base_url: str = "http://localhost:8000/media"
    s3_endpoint: Optional[str] = None
    s3_region: Optional[str] = None
    s3_bucket: Optional[str] = None
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None

    # Auth
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24 * 7

    # Providers
    llm_provider: str = "mock"
    llm_api_key: Optional[str] = None
    llm_model: str = "gpt-4o-mini"
    llm_base_url: Optional[str] = None

    image_provider: str = "mock"
    image_api_key: Optional[str] = None
    image_model: Optional[str] = None

    video_provider: str = "mock"
    video_api_key: Optional[str] = None
    video_model: Optional[str] = None

    tts_provider: str = "mock"
    tts_api_key: Optional[str] = None
    tts_voice_male: str = "en-US-male"
    tts_voice_female: str = "en-US-female"

    music_provider: str = "mock"
    music_api_key: Optional[str] = None
    music_model: Optional[str] = None

    # Payments — Razorpay (secrets read from env only; never exposed via API)
    razorpay_key_id: Optional[str] = None
    razorpay_key_secret: Optional[str] = None
    razorpay_webhook_secret: Optional[str] = None
    payment_provider: str = "razorpay"

    # Email / notifications
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: str = "noreply@hackroot.studio"
    email_provider: str = "mock"  # mock | smtp

    # Rendering
    ffmpeg_bin: str = "ffmpeg"
    ffprobe_bin: str = "ffprobe"
    video_codec: str = "libx264"
    video_preset: str = "medium"
    video_crf: int = 20
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"

    # Defaults
    default_duration: int = 20
    default_aspect_ratio: str = "9:16"
    default_language: str = "English"
    default_style: str = "Cinematic"

    # Limits
    max_upload_size_mb: int = 50
    rate_limit_per_minute: int = 60
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Telemetry
    log_level: str = "INFO"
    sentry_dsn: Optional[str] = None

    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def async_database_url(self) -> str:
        """DATABASE_URL normalized for the async SQLAlchemy engine.

        Render (and most managed Postgres) injects a sync `postgres://` URI.
        The async engine requires the `postgresql+asyncpg://` dialect, so we
        coerce the scheme here without altering other providers (e.g. sqlite).
        """
        url = self.database_url
        if url.startswith("postgres://"):
            return "postgresql+asyncpg://" + url[len("postgres://"):]
        if url.startswith("postgresql://") and "+asyncpg" not in url:
            return "postgresql+asyncpg://" + url[len("postgresql://"):]
        return url

    def validate(self) -> None:
        """Fail fast in production if critical configuration is missing/insecure.

        Raises RuntimeError so the process refuses to start rather than run with
        dev defaults (which would silently use `change-me` secrets).
        """
        if self.app_env != "production":
            return
        if not self.app_secret_key or self.app_secret_key == "change-me":
            raise RuntimeError("APP_SECRET_KEY must be set to a strong value in production.")
        if not self.jwt_secret or self.jwt_secret == "change-me":
            raise RuntimeError("JWT_SECRET must be set to a strong value in production.")
        if not self.database_url or "change-me" in self.database_url:
            raise RuntimeError("DATABASE_URL must be set to a real production database in production.")


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.validate()
    return s


settings = get_settings()

"""Provider configuration model — stores which provider is active for each role."""
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProviderConfig(Base):
    __tablename__ = "provider_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    role: Mapped[str] = mapped_column(String(32), index=True, nullable=False)  # llm/image/video/tts/music
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    config_json: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

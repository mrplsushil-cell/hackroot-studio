"""Template model — preconfigured video templates."""
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(64), nullable=True)
    preview_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Defaults
    default_duration: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    default_aspect_ratio: Mapped[str] = mapped_column(String(16), default="9:16", nullable=False)
    default_style: Mapped[str] = mapped_column(String(64), default="Cinematic", nullable=False)
    default_voice: Mapped[str] = mapped_column(String(16), default="female", nullable=False)
    default_language: Mapped[str] = mapped_column(String(32), default="English", nullable=False)

    # Structure
    scene_count: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    scene_blueprint: Mapped[str] = mapped_column(Text, nullable=False)  # JSON
    cta_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    caption_style: Mapped[str | None] = mapped_column(String(64), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

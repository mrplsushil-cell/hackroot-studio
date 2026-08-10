"""Video model."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    negative_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)

    duration: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    aspect_ratio: Mapped[str] = mapped_column(String(16), default="9:16", nullable=False)
    language: Mapped[str] = mapped_column(String(32), default="English", nullable=False)
    style: Mapped[str] = mapped_column(String(64), default="Cinematic", nullable=False)
    voice: Mapped[str] = mapped_column(String(16), default="female", nullable=False)  # male/female/none

    brand_kit_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("brand_kits.id", ondelete="SET NULL"), nullable=True
    )
    template_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("templates.id", ondelete="SET NULL"), nullable=True
    )

    # Output paths
    output_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    thumbnail_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resolution: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Cached plan & script (JSON text)
    plan_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    script: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    owner = relationship("User", backref="videos")
    brand_kit = relationship("BrandKit", backref="videos")
    template = relationship("Template", backref="videos")
    jobs = relationship(
        "VideoJob", back_populates="video", cascade="all, delete-orphan", order_by="VideoJob.id.desc()"
    )
    scenes = relationship(
        "VideoScene",
        back_populates="video",
        cascade="all, delete-orphan",
        order_by="VideoScene.scene_number",
    )

    def __repr__(self) -> str:
        return f"<Video {self.id} {self.title!r}>"

"""Video scene model."""
from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class VideoScene(Base):
    __tablename__ = "video_scenes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    video_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("videos.id", ondelete="CASCADE"), index=True, nullable=False
    )

    scene_number: Mapped[int] = mapped_column(Integer, nullable=False)
    duration: Mapped[float] = mapped_column(Float, nullable=False)

    # Script/plan content
    visual_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    negative_visual_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    voiceover: Mapped[str | None] = mapped_column(Text, nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    camera_movement: Mapped[str | None] = mapped_column(String(64), nullable=True)
    transition: Mapped[str | None] = mapped_column(String(64), nullable=True)
    music_intensity: Mapped[str | None] = mapped_column(String(16), nullable=True)  # low/med/high

    # Asset paths after generation
    image_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    voice_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    video_clip_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Effect parameters
    zoom_from: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    zoom_to: Mapped[float] = mapped_column(Float, default=1.1, nullable=False)
    pan_x: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    pan_y: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    video = relationship("Video", back_populates="scenes")

    def __repr__(self) -> str:
        return f"<VideoScene {self.scene_number} video={self.video_id}>"

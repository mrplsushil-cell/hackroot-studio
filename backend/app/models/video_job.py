"""Video job model and step/status enums."""
import enum
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class VideoJobStatus(str, enum.Enum):
    DRAFT = "draft"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VideoJobStep(str, enum.Enum):
    ANALYZING_PROMPT = "analyzing_prompt"
    CREATING_BRIEF = "creating_brief"
    CREATING_SCRIPT = "creating_script"
    PLANNING_SCENES = "planning_scenes"
    GENERATING_VISUALS = "generating_visuals"
    GENERATING_VOICE = "generating_voice"
    GENERATING_CAPTIONS = "generating_captions"
    SELECTING_MUSIC = "selecting_music"
    RENDERING_VIDEO = "rendering_video"
    QUALITY_CHECK = "quality_check"
    FINALIZING = "finalizing"
    COMPLETED = "completed"


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    """Persist the enum *values* (lowercase) rather than the member names.

    The Postgres types were created from the values (e.g. 'queued'), so without
    this SQLAlchemy would emit the member name ('QUEUED') and the insert fails
    with InvalidTextRepresentationError.
    """
    return [m.value for m in enum_cls]


class VideoJob(Base):
    __tablename__ = "video_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    video_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("videos.id", ondelete="CASCADE"), index=True, nullable=False
    )

    status: Mapped[VideoJobStatus] = mapped_column(
        Enum(VideoJobStatus, name="video_job_status",
             values_callable=_enum_values),
        default=VideoJobStatus.DRAFT,
        nullable=False,
        index=True,
    )
    current_step: Mapped[VideoJobStep | None] = mapped_column(
        Enum(VideoJobStep, name="video_job_step", values_callable=_enum_values),
        nullable=True,
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0-100

    celery_task_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_step: Mapped[str | None] = mapped_column(String(64), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    video = relationship("Video", back_populates="jobs")

    def __repr__(self) -> str:
        return f"<VideoJob {self.id} video={self.video_id} {self.status.value}>"

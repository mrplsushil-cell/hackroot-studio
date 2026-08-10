"""Generation log model — detailed per-step logs for debugging."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GenerationLog(Base):
    __tablename__ = "generation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("video_jobs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    level: Mapped[str] = mapped_column(String(16), default="info", nullable=False)
    step: Mapped[str | None] = mapped_column(String(64), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

"""Asset model (uploads, generated images, etc.)."""
from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (Index("ix_assets_owner_video", "owner_id", "video_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # image | video | audio | logo
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)

    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)

    video_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("videos.id", ondelete="SET NULL"), nullable=True
    )

    # Explicit user-controlled ordering within a project (product image order).
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    owner = relationship("User", backref="assets")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Asset {self.id} {self.name!r} kind={self.kind}>"

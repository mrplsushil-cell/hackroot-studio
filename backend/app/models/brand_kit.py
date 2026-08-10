"""BrandKit model."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BrandKit(Base):
    __tablename__ = "brand_kits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    brand_voice: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    primary_color: Mapped[str | None] = mapped_column(String(16), nullable=True)
    secondary_color: Mapped[str | None] = mapped_column(String(16), nullable=True)
    accent_color: Mapped[str | None] = mapped_column(String(16), nullable=True)
    font_family: Mapped[str | None] = mapped_column(String(128), nullable=True)

    logo_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    website: Mapped[str | None] = mapped_column(String(512), nullable=True)
    social_links: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON

    is_default: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    owner = relationship("User", backref="brand_kits")

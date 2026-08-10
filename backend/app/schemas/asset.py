"""Asset schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.storage import get_storage


class AssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    original_filename: str | None = None
    kind: str
    mime_type: str
    path: str
    file_size_bytes: int
    width: int | None
    height: int | None
    duration: float | None
    video_id: int | None
    sort_order: int = 0
    description: str | None
    created_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def url(self) -> str:
        """Public URL for previewing the asset."""
        try:
            return get_storage().url_for(self.path)
        except Exception:  # pragma: no cover - storage misconfiguration
            return self.path


class AssetReorderRequest(BaseModel):
    """Explicit ordering: full list of asset ids in the desired order."""

    asset_ids: list[int] = Field(min_length=1, max_length=200)


class AssetUpdateRequest(BaseModel):
    description: str | None = Field(default=None, max_length=2000)
    video_id: int | None = None

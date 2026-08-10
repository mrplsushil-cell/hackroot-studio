"""Brand kit schemas."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class BrandKitCreate(BaseModel):
    name: str
    brand_voice: str | None = None
    description: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    accent_color: str | None = None
    font_family: str | None = None
    website: str | None = None
    social_links: str | None = None
    is_default: bool = False


class BrandKitUpdate(BaseModel):
    # All fields optional for partial updates (frontend sends the full object,
    # but the API should accept e.g. {"is_default": true} on its own).
    name: str | None = None
    brand_voice: str | None = None
    description: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    accent_color: str | None = None
    font_family: str | None = None
    website: str | None = None
    social_links: str | None = None
    is_default: bool | None = None


class BrandKitOut(BrandKitCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    logo_path: str | None
    created_at: datetime
    updated_at: datetime

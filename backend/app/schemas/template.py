"""Template schemas."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class TemplateCreate(BaseModel):
    """Payload for user-defined (custom) templates."""

    name: str
    description: str | None = None
    category: str | None = None
    default_duration: int = 20
    default_aspect_ratio: str = "9:16"
    default_style: str = "Cinematic"
    default_voice: str = "female"
    default_language: str = "English"
    scene_blueprint: str  # JSON array of scene descriptors
    cta_template: str | None = None
    caption_style: str | None = None


class TemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    slug: str
    name: str
    description: str | None
    category: str
    icon: str | None
    preview_url: str | None
    default_duration: int
    default_aspect_ratio: str
    default_style: str
    default_voice: str
    default_language: str
    scene_count: int
    scene_blueprint: str
    cta_template: str | None
    caption_style: str | None
    is_active: bool
    is_system: bool = True

"""Video schemas."""
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


AspectRatio = Literal["16:9", "9:16", "1:1", "4:5"]
Voice = Literal["male", "female", "none"]
Language = Literal["English", "Hindi", "Hinglish", "Punjabi"]
Style = Literal[
    "Cinematic",
    "Product Advertisement",
    "Social Media Reel",
    "Corporate",
    "Minimal",
    "Luxury",
    "Fashion",
    "Documentary",
    "Storytelling",
]


class VideoCreate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    prompt: str = Field(min_length=4, max_length=4000)
    duration: int = Field(default=20, ge=5, le=120)
    aspect_ratio: AspectRatio = "9:16"
    language: Language = "English"
    style: Style = "Cinematic"
    voice: Voice = "female"
    brand_kit_id: int | None = None
    template_id: int | None = None
    asset_ids: list[int] = Field(default_factory=list)


class SceneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    scene_number: int
    duration: float
    visual_prompt: str
    voiceover: str | None
    caption: str | None
    camera_movement: str | None
    transition: str | None
    music_intensity: str | None
    image_path: str | None
    video_clip_path: str | None


class VideoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    owner_id: int
    title: str
    prompt: str
    duration: int
    aspect_ratio: str
    language: str
    style: str
    voice: str
    output_path: str | None
    thumbnail_path: str | None
    resolution: str | None
    file_size_bytes: int | None
    created_at: datetime
    updated_at: datetime
    scenes: list[SceneOut] = Field(default_factory=list)


class VideoSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    duration: int
    aspect_ratio: str
    status: str
    thumbnail_path: str | None
    created_at: datetime


class JobStatusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    video_id: int
    status: str
    current_step: str | None
    progress: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class VideoGenerateRequest(BaseModel):
    prompt: str | None = None
    duration: int | None = None
    aspect_ratio: AspectRatio | None = None
    language: Language | None = None
    style: Style | None = None
    voice: Voice | None = None
    asset_ids: list[int] = Field(default_factory=list)


class DashboardStats(BaseModel):
    total_videos: int
    videos_generated: int
    processing: int
    failed_jobs: int
    credits_total: int
    credits_used: int
    credits_remaining: int

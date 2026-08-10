"""Provider config + AI Agents status routes."""
from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings
from app.core.deps import CurrentUser

router = APIRouter(prefix="/providers", tags=["providers"])


class ProviderInfo(BaseModel):
    role: str
    provider: str
    model: str | None
    available: bool
    requires_key: bool
    message: str | None = None


def _info(role: str, name: str, model: str | None, has_key: bool, requires_key: bool) -> ProviderInfo:
    return ProviderInfo(
        role=role, provider=name, model=model, available=True,
        requires_key=requires_key,
        message=None if has_key or not requires_key else f"Set the API key for {name} in your environment.",
    )


@router.get("", response_model=list[ProviderInfo])
async def list_providers(user: CurrentUser) -> list[ProviderInfo]:
    return [
        _info("llm", settings.llm_provider, settings.llm_model,
              bool(settings.llm_api_key), settings.llm_provider != "mock"),
        _info("image", settings.image_provider, settings.image_model,
              bool(settings.image_api_key), settings.image_provider != "mock"),
        _info("video", settings.video_provider, settings.video_model,
              bool(settings.video_api_key), settings.video_provider != "mock"),
        _info("tts", settings.tts_provider, None,
              bool(settings.tts_api_key), settings.tts_provider != "mock"),
        _info("music", settings.music_provider, settings.music_model,
              bool(settings.music_api_key), settings.music_provider != "mock"),
    ]


# ---------------------------------------------------------------------------
# AI Agents (logical service descriptions)
# ---------------------------------------------------------------------------
agents_router = APIRouter(prefix="/agents", tags=["agents"])


class AgentInfo(BaseModel):
    id: str
    name: str
    role: str
    status: str
    description: str


_AGENTS = [
    {"id": "director", "name": "Video Director",
     "role": "Plans structure, tone, and pacing for the entire video.",
     "description": "Reads your prompt, asks the right questions, and produces a complete creative brief."},
    {"id": "analyzer", "name": "Prompt Analyzer",
     "role": "Turns a raw prompt into a structured brief.",
     "description": "Extracts intent, audience, product, and constraints, then hands a clean brief to the Director."},
    {"id": "script", "name": "Script Writer",
     "role": "Generates the voiceover and on-screen copy.",
     "description": "Writes tight, on-brand scripts sized to the requested duration and language."},
    {"id": "scenes", "name": "Scene Planner",
     "role": "Divides the video into scenes with timing and transitions.",
     "description": "Splits the script into scenes, assigns durations, and picks camera movements."},
    {"id": "visual", "name": "Visual Director",
     "role": "Generates or sources imagery for every scene.",
     "description": "Calls image providers, uploads product images, and curates visuals for the brand."},
    {"id": "voice", "name": "Voice Director",
     "role": "Synthesises the voiceover in the chosen language and voice.",
     "description": "Matches voice tone to brand voice and synchronises with scene timing."},
    {"id": "captions", "name": "Caption Generator",
     "role": "Writes and times on-screen captions.",
     "description": "Produces SRT/VTT captions synced to each scene and the spoken voiceover."},
    {"id": "editor", "name": "AI Editor",
     "role": "Assembles the final MP4 via FFmpeg.",
     "description": "Renders scenes, mixes audio, burns captions, applies transitions and logo."},
    {"id": "qc", "name": "Quality Control",
     "role": "Validates the final output before delivery.",
     "description": "Checks duration, audio, captions, resolution, and aspect ratio."},
]


@agents_router.get("", response_model=list[AgentInfo])
async def list_agents(user: CurrentUser) -> list[AgentInfo]:
    return [AgentInfo(id=a["id"], name=a["name"], role=a["role"],
                      status="ready", description=a["description"]) for a in _AGENTS]

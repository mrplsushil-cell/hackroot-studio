"""Pydantic schemas for structured AI JSON outputs.

These describe the *runtime contract* between the LLM providers and the
pipeline director. Field names match exactly what `VideoDirector` requests in
its system prompts and what the renderer later consumes, so any provider
(mock or real) can be validated against them.

Extra keys returned by a model are preserved rather than rejected, so a richer
real-world provider stays compatible.
"""
from pydantic import BaseModel, ConfigDict, Field, field_validator


class VideoBrief(BaseModel):
    """The output of the Prompt Analyzer (step 1a)."""

    model_config = ConfigDict(extra="allow")

    title: str = Field(description="A catchy title for the video.")
    logline: str = Field(default="", description="One-sentence summary of the video.")
    target_audience: str = Field(default="general", description="Primary audience.")
    tone: str = Field(default="energetic and professional", description="Overall tone.")
    duration: int = Field(default=20, ge=1, description="Ideal length in seconds.")
    aspect_ratio: str = Field(default="9:16", description="Target aspect ratio.")
    language: str = Field(default="English", description="Spoken/caption language.")


class ScenePlan(BaseModel):
    """A single scene produced by the Scene Planner (step 1b)."""

    model_config = ConfigDict(extra="allow")

    scene_number: int = Field(ge=1, description="Sequential number, starting at 1.")
    duration: float = Field(gt=0, description="Duration of this scene in seconds.")
    beat: str = Field(default="", description="Narrative beat, e.g. Hook or Call to Action.")
    voiceover: str = Field(default="", description="Spoken script for this scene.")
    caption: str = Field(default="", description="On-screen caption text.")
    visual_prompt: str = Field(description="Prompt sent to the image/video generator.")
    camera_movement: str = Field(default="static", description="e.g. slow_zoom_in, static.")
    transition: str = Field(default="none", description="Transition into this scene.")
    music_intensity: str = Field(default="med", description="low | med | high.")
    zoom_from: float = Field(default=1.0, gt=0, description="Ken Burns start scale.")
    zoom_to: float = Field(default=1.0, gt=0, description="Ken Burns end scale.")


class VideoScript(BaseModel):
    """The full structured script returned by the script/scene planner."""

    model_config = ConfigDict(extra="allow")

    scenes: list[ScenePlan] = Field(min_length=1, description="Ordered scene list.")
    total_words: int = Field(default=0, ge=0, description="Approximate word count.")
    language: str = Field(default="English")
    style: str = Field(default="Cinematic")
    voice: str = Field(default="female")

    @field_validator("scenes")
    @classmethod
    def _renumber(cls, scenes: list[ScenePlan]) -> list[ScenePlan]:
        """Guarantee contiguous 1..N numbering regardless of provider output."""
        for i, scene in enumerate(scenes, start=1):
            scene.scene_number = i
        return scenes

    @property
    def total_duration(self) -> float:
        return round(sum(s.duration for s in self.scenes), 2)

"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-01-01
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("full_name", sa.String(255)),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
        sa.Column("is_superuser", sa.Boolean, default=False, nullable=False),
        sa.Column("credits_total", sa.Integer, default=100, nullable=False),
        sa.Column("credits_used", sa.Integer, default=0, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "brand_kits",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("owner_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("brand_voice", sa.String(255)),
        sa.Column("description", sa.Text),
        sa.Column("primary_color", sa.String(16)),
        sa.Column("secondary_color", sa.String(16)),
        sa.Column("accent_color", sa.String(16)),
        sa.Column("font_family", sa.String(128)),
        sa.Column("logo_path", sa.String(1024)),
        sa.Column("website", sa.String(512)),
        sa.Column("social_links", sa.Text),
        sa.Column("is_default", sa.Boolean, default=False, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "templates",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("slug", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("icon", sa.String(64)),
        sa.Column("preview_url", sa.String(512)),
        sa.Column("default_duration", sa.Integer, default=20, nullable=False),
        sa.Column("default_aspect_ratio", sa.String(16), default="9:16", nullable=False),
        sa.Column("default_style", sa.String(64), default="Cinematic", nullable=False),
        sa.Column("default_voice", sa.String(16), default="female", nullable=False),
        sa.Column("default_language", sa.String(32), default="English", nullable=False),
        sa.Column("scene_count", sa.Integer, default=4, nullable=False),
        sa.Column("scene_blueprint", sa.Text, nullable=False),
        sa.Column("cta_template", sa.Text),
        sa.Column("caption_style", sa.String(64)),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
        sa.Column("is_system", sa.Boolean, default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "videos",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("owner_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("prompt", sa.Text, nullable=False),
        sa.Column("negative_prompt", sa.Text),
        sa.Column("duration", sa.Integer, default=20, nullable=False),
        sa.Column("aspect_ratio", sa.String(16), default="9:16", nullable=False),
        sa.Column("language", sa.String(32), default="English", nullable=False),
        sa.Column("style", sa.String(64), default="Cinematic", nullable=False),
        sa.Column("voice", sa.String(16), default="female", nullable=False),
        sa.Column("brand_kit_id", sa.Integer, sa.ForeignKey("brand_kits.id", ondelete="SET NULL")),
        sa.Column("template_id", sa.Integer, sa.ForeignKey("templates.id", ondelete="SET NULL")),
        sa.Column("output_path", sa.String(1024)),
        sa.Column("thumbnail_path", sa.String(1024)),
        sa.Column("file_size_bytes", sa.Integer),
        sa.Column("resolution", sa.String(32)),
        sa.Column("plan_json", sa.Text),
        sa.Column("script", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "video_scenes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("video_id", sa.Integer, sa.ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("scene_number", sa.Integer, nullable=False),
        sa.Column("duration", sa.Float, nullable=False),
        sa.Column("visual_prompt", sa.Text, nullable=False),
        sa.Column("negative_visual_prompt", sa.Text),
        sa.Column("voiceover", sa.Text),
        sa.Column("caption", sa.Text),
        sa.Column("camera_movement", sa.String(64)),
        sa.Column("transition", sa.String(64)),
        sa.Column("music_intensity", sa.String(16)),
        sa.Column("image_path", sa.String(1024)),
        sa.Column("voice_path", sa.String(1024)),
        sa.Column("video_clip_path", sa.String(1024)),
        sa.Column("zoom_from", sa.Float, default=1.0, nullable=False),
        sa.Column("zoom_to", sa.Float, default=1.1, nullable=False),
        sa.Column("pan_x", sa.Float, default=0.0, nullable=False),
        sa.Column("pan_y", sa.Float, default=0.0, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "video_jobs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("video_id", sa.Integer, sa.ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("status", sa.Enum("draft", "queued", "processing", "completed", "failed", "cancelled",
                                   name="video_job_status"), default="draft", nullable=False, index=True),
        sa.Column("current_step", sa.Enum(
            "analyzing_prompt", "creating_brief", "creating_script", "planning_scenes",
            "generating_visuals", "generating_voice", "generating_captions", "selecting_music",
            "rendering_video", "quality_check", "finalizing", "completed",
            name="video_job_step")),
        sa.Column("progress", sa.Integer, default=0, nullable=False),
        sa.Column("celery_task_id", sa.String(128)),
        sa.Column("error_message", sa.Text),
        sa.Column("error_step", sa.String(64)),
        sa.Column("retry_count", sa.Integer, default=0, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "assets",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("owner_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("mime_type", sa.String(128), nullable=False),
        sa.Column("path", sa.String(1024), nullable=False),
        sa.Column("file_size_bytes", sa.Integer, nullable=False),
        sa.Column("width", sa.Integer),
        sa.Column("height", sa.Integer),
        sa.Column("duration", sa.Integer),
        sa.Column("video_id", sa.Integer, sa.ForeignKey("videos.id", ondelete="SET NULL")),
        sa.Column("description", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "provider_configs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("role", sa.String(32), nullable=False, index=True),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("model", sa.String(128)),
        sa.Column("config_json", sa.String(2048)),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "generation_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("job_id", sa.Integer, sa.ForeignKey("video_jobs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("level", sa.String(16), default="info", nullable=False),
        sa.Column("step", sa.String(64)),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("detail", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("generation_logs")
    op.drop_table("provider_configs")
    op.drop_table("assets")
    op.drop_table("video_jobs")
    op.drop_table("video_scenes")
    op.drop_table("videos")
    op.drop_table("templates")
    op.drop_table("brand_kits")
    op.drop_table("users")

"""Video CRUD + generation routes."""
from __future__ import annotations
import json
import os
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.deps import CurrentUser, DbSession
from app.jobs.tasks import enqueue_generation
from app.models import Asset, Video, VideoJob, VideoJobStatus
from app.schemas.video import (
    DashboardStats,
    JobStatusOut,
    VideoCreate,
    VideoGenerateRequest,
    VideoOut,
    VideoSummary,
)
from app.utils.files import safe_filename
from app.utils.uploads import MAX_IMAGES_PER_PROJECT

router = APIRouter(prefix="/videos", tags=["videos"])


# ---------------------------------------------------------------------------
# Dashboard stats
# ---------------------------------------------------------------------------
@router.get("/_stats", response_model=DashboardStats)
async def stats(user: CurrentUser, db: DbSession) -> DashboardStats:
    total = (await db.execute(
        select(func.count(Video.id)).where(Video.owner_id == user.id)
    )).scalar_one()
    jobs = (await db.execute(
        select(VideoJob).join(Video).where(Video.owner_id == user.id)
    )).scalars().all()
    completed = sum(1 for j in jobs if j.status == VideoJobStatus.COMPLETED)
    processing = sum(1 for j in jobs if j.status in (VideoJobStatus.QUEUED, VideoJobStatus.PROCESSING))
    failed = sum(1 for j in jobs if j.status == VideoJobStatus.FAILED)
    return DashboardStats(
        total_videos=total,
        videos_generated=completed,
        processing=processing,
        failed_jobs=failed,
        credits_total=user.credits_total,
        credits_used=user.credits_used,
        credits_remaining=max(0, user.credits_total - user.credits_used),
    )


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------
@router.post("", response_model=VideoOut, status_code=201)
async def create_video(payload: VideoCreate, user: CurrentUser, db: DbSession) -> VideoOut:
    title = payload.title or (payload.prompt[:60].strip() or "Untitled")
    video = Video(
        owner_id=user.id,
        title=title,
        prompt=payload.prompt,
        duration=payload.duration,
        aspect_ratio=payload.aspect_ratio,
        language=payload.language,
        style=payload.style,
        voice=payload.voice,
        brand_kit_id=payload.brand_kit_id,
        template_id=payload.template_id,
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    if payload.asset_ids:
        await _attach_assets(db, user.id, video.id, payload.asset_ids)
    return await _video_out(db, video.id)


async def _video_out(db, video_id: int) -> VideoOut:
    """Serialize a video with its scenes eagerly loaded (async-safe)."""
    v = (await db.execute(
        select(Video).options(selectinload(Video.scenes)).where(Video.id == video_id)
    )).scalar_one()
    return VideoOut.model_validate(v)


async def _attach_assets(db, user_id: int, video_id: int, asset_ids: list[int]) -> None:
    """Attach owned image assets to a project, preserving the requested order."""
    if len(set(asset_ids)) != len(asset_ids):
        raise HTTPException(400, "asset_ids contains duplicates")
    if len(asset_ids) > MAX_IMAGES_PER_PROJECT:
        raise HTTPException(
            400, f"At most {MAX_IMAGES_PER_PROJECT} images can be attached to a project"
        )
    res = await db.execute(
        select(Asset).where(Asset.id.in_(asset_ids), Asset.owner_id == user_id)
    )
    found = {a.id: a for a in res.scalars().all()}
    missing = [i for i in asset_ids if i not in found]
    if missing:
        raise HTTPException(404, f"Assets not found or not owned by you: {missing}")
    for order, aid in enumerate(asset_ids):
        found[aid].video_id = video_id
        found[aid].sort_order = order
    await db.commit()


@router.get("", response_model=list[VideoSummary])
async def list_videos(
    user: CurrentUser,
    db: DbSession,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[VideoSummary]:
    res = await db.execute(
        select(Video)
        .where(Video.owner_id == user.id)
        .order_by(Video.created_at.desc())
        .limit(limit).offset(offset)
    )
    videos = res.scalars().all()
    # attach latest job status
    out: list[VideoSummary] = []
    for v in videos:
        j = (await db.execute(
            select(VideoJob).where(VideoJob.video_id == v.id)
            .order_by(VideoJob.id.desc()).limit(1)
        )).scalar_one_or_none()
        s = VideoSummary(
            id=v.id, title=v.title, duration=v.duration, aspect_ratio=v.aspect_ratio,
            status=(j.status.value if j else "draft"),
            thumbnail_path=v.thumbnail_path, created_at=v.created_at,
        )
        out.append(s)
    return out


@router.get("/{video_id}", response_model=VideoOut)
async def get_video(video_id: int, user: CurrentUser, db: DbSession) -> VideoOut:
    v = (await db.execute(
        select(Video).where(Video.id == video_id, Video.owner_id == user.id)
    )).scalar_one_or_none()
    if v is None:
        raise HTTPException(404, "Video not found")
    return await _video_out(db, v.id)


@router.delete("/{video_id}", status_code=204)
async def delete_video(video_id: int, user: CurrentUser, db: DbSession):  # noqa: ANN201 — `-> None` breaks FastAPI 204 under future-annotations
    v = (await db.execute(
        select(Video).where(Video.id == video_id, Video.owner_id == user.id)
    )).scalar_one_or_none()
    if v is None:
        raise HTTPException(404, "Video not found")
    await db.delete(v)
    await db.commit()


@router.patch("/{video_id}/rename")
async def rename_video(video_id: int, payload: dict, user: CurrentUser, db: DbSession) -> dict:
    v = (await db.execute(
        select(Video).where(Video.id == video_id, Video.owner_id == user.id)
    )).scalar_one_or_none()
    if v is None:
        raise HTTPException(404, "Video not found")
    new_title = (payload.get("title") or "").strip()[:255]
    if not new_title:
        raise HTTPException(400, "title is required")
    v.title = new_title
    await db.commit()
    return {"id": v.id, "title": v.title}


@router.post("/{video_id}/duplicate", response_model=VideoOut, status_code=201)
async def duplicate_video(video_id: int, user: CurrentUser, db: DbSession) -> VideoOut:
    v = (await db.execute(
        select(Video).where(Video.id == video_id, Video.owner_id == user.id)
    )).scalar_one_or_none()
    if v is None:
        raise HTTPException(404, "Video not found")
    copy = Video(
        owner_id=v.owner_id,
        title=f"{v.title} (copy)",
        prompt=v.prompt, negative_prompt=v.negative_prompt,
        duration=v.duration, aspect_ratio=v.aspect_ratio,
        language=v.language, style=v.style, voice=v.voice,
        brand_kit_id=v.brand_kit_id, template_id=v.template_id,
    )
    db.add(copy)
    await db.commit()
    await db.refresh(copy)
    return await _video_out(db, copy.id)


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------
@router.post("/{video_id}/generate", response_model=JobStatusOut, status_code=202)
async def start_generation(
    video_id: int, payload: VideoGenerateRequest | None = None,
    user: CurrentUser = None, db: DbSession = None,
) -> JobStatusOut:
    v = (await db.execute(
        select(Video).where(Video.id == video_id, Video.owner_id == user.id)
    )).scalar_one_or_none()
    if v is None:
        raise HTTPException(404, "Video not found")
    if payload:
        if payload.prompt:
            v.prompt = payload.prompt
        if payload.duration:
            v.duration = payload.duration
        if payload.aspect_ratio:
            v.aspect_ratio = payload.aspect_ratio
        if payload.language:
            v.language = payload.language
        if payload.style:
            v.style = payload.style
        if payload.voice:
            v.voice = payload.voice
        if payload.asset_ids:
            await _attach_assets(db, user.id, v.id, payload.asset_ids)

    job = VideoJob(video_id=v.id, status=VideoJobStatus.QUEUED, progress=0)
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Enforce credit balance + plan video limit before queuing.
    from app.services.credits import can_generate, credits_for_duration
    allowed, cost, reason = await can_generate(db, user, v.duration)
    if not allowed:
        await db.delete(job)
        await db.commit()
        raise HTTPException(
            status_code=402,
            detail={"error": "credits_exhausted", "message": reason or "Insufficient credits", "cost": cost},
        )

    try:
        enqueue_generation(job_id=job.id, video_id=v.id)
    except Exception as e:
        # If Celery broker is unreachable, fall back to in-process generation
        # so the user can still get a video in dev. In production this surfaces
        # as a 503.
        from app.jobs.tasks import generate_video_task
        from app.config import settings as s
        if s.app_env == "development":
            generate_video_task.delay(job_id=job.id, video_id=v.id)
        else:
            raise HTTPException(503, f"Job queue unavailable: {e}") from e
    return JobStatusOut.model_validate(job)


@router.get("/{video_id}/status", response_model=JobStatusOut)
async def get_status(video_id: int, user: CurrentUser, db: DbSession) -> JobStatusOut:
    v = (await db.execute(
        select(Video).where(Video.id == video_id, Video.owner_id == user.id)
    )).scalar_one_or_none()
    if v is None:
        raise HTTPException(404, "Video not found")
    job = (await db.execute(
        select(VideoJob).where(VideoJob.video_id == v.id)
        .order_by(VideoJob.id.desc()).limit(1)
    )).scalar_one_or_none()
    if job is None:
        raise HTTPException(404, "No job for this video")
    return JobStatusOut.model_validate(job)


@router.get("/{video_id}/download")
async def download_video(video_id: int, user: CurrentUser, db: DbSession) -> FileResponse:
    v = (await db.execute(
        select(Video).where(Video.id == video_id, Video.owner_id == user.id)
    )).scalar_one_or_none()
    if v is None:
        raise HTTPException(404, "Video not found")
    if not v.output_path or not os.path.exists(v.output_path):
        raise HTTPException(404, "Video not yet generated")
    fname = safe_filename(f"{v.title or 'video'}.mp4")
    return FileResponse(v.output_path, media_type="video/mp4", filename=fname)


@router.get("/{video_id}/thumbnail")
async def get_thumbnail(video_id: int, user: CurrentUser, db: DbSession) -> FileResponse:
    v = (await db.execute(
        select(Video).where(Video.id == video_id, Video.owner_id == user.id)
    )).scalar_one_or_none()
    if v is None:
        raise HTTPException(404, "Video not found")
    if not v.thumbnail_path or not os.path.exists(v.thumbnail_path):
        raise HTTPException(404, "Thumbnail not available")
    return FileResponse(v.thumbnail_path, media_type="image/jpeg")

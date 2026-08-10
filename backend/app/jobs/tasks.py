"""Video generation background tasks."""
from __future__ import annotations
import asyncio
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from celery import shared_task
from sqlalchemy import select

from app.config import settings
from app.database import AsyncSessionLocal, engine
from app.jobs.celery_app import celery_app
from app.models import GenerationLog, User, Video, VideoJob, VideoJobStatus
from app.pipeline.director import VideoDirector, VideoDirectorError
from app.storage import get_storage
from app.utils.files import safe_filename

log = logging.getLogger("hackroot.jobs")


def run_async(coro):
    """Run a coroutine from the synchronous Celery worker.

    Each call gets a fresh event loop, so the async engine's pooled asyncpg
    connections (which bind themselves to the loop that created them) must be
    disposed before the loop closes. Without this, the second DB call in a task
    raises "got Future attached to a different loop".

    Progress callbacks fire from *inside* the pipeline's own running loop, where
    `asyncio.run()` is illegal. In that case we run the coroutine on a separate
    thread with its own loop and wait for it, keeping the callback synchronous
    from the caller's point of view.
    """
    async def _wrapped():
        try:
            return await coro
        finally:
            await engine.dispose()

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_wrapped())

    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(_wrapped())).result()


def _set_progress(job_id: int, step: str, pct: int, status: VideoJobStatus | None = None) -> None:
    """Update job progress synchronously from the worker."""
    async def _run() -> None:
        async with AsyncSessionLocal() as db:
            res = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
            job = res.scalar_one_or_none()
            if job is None:
                return
            job.current_step = step  # type: ignore[assignment]
            job.progress = pct
            if status:
                job.status = status
            if status == VideoJobStatus.PROCESSING and job.started_at is None:
                job.started_at = datetime.now(timezone.utc)
            if status in (VideoJobStatus.COMPLETED, VideoJobStatus.FAILED, VideoJobStatus.CANCELLED):
                job.completed_at = datetime.now(timezone.utc)
            await db.commit()
    run_async(_run())


def _append_log(job_id: int, level: str, step: str | None, message: str, detail: str | None = None) -> None:
    async def _run() -> None:
        async with AsyncSessionLocal() as db:
            db.add(GenerationLog(job_id=job_id, level=level, step=step, message=message, detail=detail))
            await db.commit()
    run_async(_run())


def _finalize_success(job_id: int, video_id: int, result: dict) -> None:
    async def _run() -> None:
        from app.models import VideoScene

        plan = {}
        try:
            plan = json.loads(result.get("plan_json") or "{}")
        except json.JSONDecodeError:
            log.warning("plan_json was not valid JSON for video %s", video_id)
        scenes = (plan.get("script") or {}).get("scenes") or []

        async with AsyncSessionLocal() as db:
            v = (await db.execute(select(Video).where(Video.id == video_id))).scalar_one()
            u = (await db.execute(select(User).where(User.id == v.owner_id))).scalar_one()
            v.output_path = result["output_path"]
            v.thumbnail_path = result.get("thumbnail_path")
            v.file_size_bytes = result.get("file_size_bytes")
            v.resolution = f"{result['width']}x{result['height']}"
            v.plan_json = result.get("plan_json")
            v.script = json.dumps(scenes, ensure_ascii=False)
            if result.get("title"):
                v.title = str(result["title"])[:255]

            # Replace persisted scenes with the rendered plan.
            existing = (await db.execute(
                select(VideoScene).where(VideoScene.video_id == video_id)
            )).scalars().all()
            for old in existing:
                await db.delete(old)
            for i, s in enumerate(scenes, start=1):
                db.add(VideoScene(
                    video_id=video_id,
                    scene_number=int(s.get("scene_number") or i),
                    duration=float(s.get("duration") or 0.0),
                    visual_prompt=str(s.get("visual_prompt") or ""),
                    negative_visual_prompt=s.get("negative_visual_prompt"),
                    voiceover=s.get("voiceover"),
                    caption=s.get("caption"),
                    camera_movement=s.get("camera_movement"),
                    transition=s.get("transition"),
                    music_intensity=s.get("music_intensity"),
                    image_path=s.get("image_path"),
                    voice_path=s.get("voice_path"),
                    video_clip_path=s.get("video_clip_path"),
                    zoom_from=float(s.get("zoom_from") or 1.0),
                    zoom_to=float(s.get("zoom_to") or 1.1),
                    pan_x=float(s.get("pan_x") or 0.0),
                    pan_y=float(s.get("pan_y") or 0.0),
                ))

            j = (await db.execute(select(VideoJob).where(VideoJob.id == job_id))).scalar_one()
            j.status = VideoJobStatus.COMPLETED
            j.progress = 100
            j.completed_at = datetime.now(timezone.utc)
            j.current_step = "completed"  # type: ignore[assignment]
            await db.commit()

            # Consume credits for the generation (banded by duration) + notify.
            try:
                from app.models import Notification
                from app.services.credits import consume_credits
                await consume_credits(db, u, v.duration, reference_type="video", reference_id=v.id, commit=False)
                db.add(Notification(
                    user_id=v.owner_id, type="video_ready",
                    title="Your video is ready",
                    body=f"\"{v.title}\" finished rendering.",
                    link=f"/library?video={v.id}",
                ))
                from app.services import email_events
                email_events.send_video_ready(u, v.title or "Your video", v.id)
                await db.commit()
            except Exception as e:  # noqa: BLE001
                log.warning("Credit/notify post-step failed for video %s: %s", v.id, e)
    run_async(_run())


async def _plan_watermark(db, user_id: int) -> bool:
    """Return True if the user's current plan applies a watermark."""
    from app.models import Subscription, SubscriptionPlan
    from app.services.plans import FREE_SLUG
    from sqlalchemy.orm import selectinload
    res = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == user_id, Subscription.status == "active")
        .options(selectinload(Subscription.plan))
        .order_by(Subscription.current_period_end.desc())
    )
    sub = res.scalars().first()
    if sub and sub.plan:
        return bool(sub.plan.has_watermark)
    res = await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.slug == FREE_SLUG))
    plan = res.scalar_one_or_none()
    return bool(plan and plan.has_watermark)


def _finalize_failure(job_id: int, video_id: int, step: str, message: str) -> None:
    async def _run() -> None:
        async with AsyncSessionLocal() as db:
            j = (await db.execute(select(VideoJob).where(VideoJob.id == job_id))).scalar_one()
            j.status = VideoJobStatus.FAILED
            j.error_step = step
            j.error_message = message
            j.completed_at = datetime.now(timezone.utc)
            await db.commit()
    run_async(_run())


@celery_app.task(name="app.jobs.tasks.generate_video_task", bind=True, max_retries=2)
def generate_video_task(self, *, job_id: int, video_id: int) -> dict:
    """Top-level Celery task. Orchestrates the full pipeline."""
    log.info("Starting generation job_id=%s video_id=%s", job_id, video_id)

    async def _load() -> dict:
        """Load everything the pipeline needs before leaving the session."""
        from app.models import Asset, BrandKit

        async with AsyncSessionLocal() as db:
            v = (await db.execute(select(Video).where(Video.id == video_id))).scalar_one()

            # Product image mode: user-uploaded images attached to this project,
            # in the order the user arranged them.
            assets = (await db.execute(
                select(Asset)
                .where(Asset.video_id == v.id, Asset.kind == "image")
                .order_by(Asset.sort_order.asc(), Asset.id.asc())
            )).scalars().all()
            storage = get_storage()
            product_images: list[str] = []
            for a in assets:
                try:
                    product_images.append(storage.open_path(a.path))
                except Exception as e:  # noqa: BLE001
                    log.warning("Skipping unreadable asset %s: %s", a.id, e)

            # Brand kit: explicit kit on the video, else the user's default.
            kit = None
            if v.brand_kit_id:
                kit = (await db.execute(
                    select(BrandKit).where(BrandKit.id == v.brand_kit_id)
                )).scalar_one_or_none()
            if kit is None:
                kit = (await db.execute(
                    select(BrandKit).where(
                        BrandKit.owner_id == v.owner_id, BrandKit.is_default.is_(True)
                    )
                )).scalar_one_or_none()

            brand_logo = None
            brand_kit_data = None
            if kit is not None:
                brand_kit_data = {
                    "name": kit.name,
                    "brand_voice": kit.brand_voice,
                    "description": kit.description,
                    "primary_color": kit.primary_color,
                    "secondary_color": kit.secondary_color,
                    "accent_color": kit.accent_color,
                    "font_family": kit.font_family,
                    "website": kit.website,
                }
                if kit.logo_path:
                    try:
                        brand_logo = storage.open_path(kit.logo_path)
                    except Exception as e:  # noqa: BLE001
                        log.warning("Brand logo unreadable: %s", e)

            return {
                "id": v.id,
                "owner_id": v.owner_id,
                "prompt": v.prompt,
                "duration": v.duration,
                "aspect_ratio": v.aspect_ratio,
                "language": v.language,
                "style": v.style,
                "voice": v.voice,
                "product_image_paths": product_images,
                "brand_logo": brand_logo,
                "brand_kit": brand_kit_data,
                "watermark": ("Made with Hackroot Studio"
                              if (await _plan_watermark(db, v.owner_id)) else None),
            }

    ctx = run_async(_load())

    director = VideoDirector(
        workdir=settings.storage_local_root,
        video_id=ctx["id"],
        user_id=ctx["owner_id"],
        job_id=job_id,
        progress_cb=lambda step, pct, msg: _set_progress(job_id, step, pct,
                                                         VideoJobStatus.PROCESSING
                                                         if pct < 100 else VideoJobStatus.COMPLETED),
    )

    try:
        _set_progress(job_id, "analyzing_prompt", 5, VideoJobStatus.PROCESSING)
        _append_log(job_id, "info", "start", f"Pipeline started for video {video_id}")
        if ctx["product_image_paths"]:
            _append_log(job_id, "info", "assets",
                        f"Product image mode: {len(ctx['product_image_paths'])} user image(s)")

        # Sync the async pipeline via asyncio.run
        result = run_async(director.run(
            prompt=ctx["prompt"],
            duration=ctx["duration"],
            aspect_ratio=ctx["aspect_ratio"],
            language=ctx["language"],
            style=ctx["style"],
            voice=ctx["voice"],
            brand_kit=ctx["brand_kit"],
            product_image_paths=ctx["product_image_paths"],
            brand_logo=ctx["brand_logo"],
            watermark=ctx.get("watermark"),
        ))
        _finalize_success(job_id, video_id, result)
        _append_log(job_id, "info", "completed", f"Video generated in {result.get('elapsed_seconds')}s")
        return result
    except VideoDirectorError as e:
        log.exception("Director failed: %s", e)
        _finalize_failure(job_id, video_id, e.step, e.user_message)
        _append_log(job_id, "error", e.step, e.user_message)
        return {"ok": False, "error": e.user_message, "step": e.step}
    except Exception as e:  # noqa: BLE001
        log.exception("Unexpected pipeline failure")
        _finalize_failure(job_id, video_id, "unknown", f"Unexpected error: {e!s}")
        _append_log(job_id, "error", "unknown", str(e))
        return {"ok": False, "error": str(e), "step": "unknown"}


def enqueue_generation(*, job_id: int, video_id: int) -> str:
    """Submit a generation job to Celery. Returns the task id."""
    async_result = generate_video_task.apply_async(
        kwargs={"job_id": job_id, "video_id": video_id},
        queue="default",
    )
    return async_result.id

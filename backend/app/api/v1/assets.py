"""Asset routes — image upload, listing, preview, delete and reordering.

Upload contract (Phase 3):
  * JPG / JPEG / PNG / WEBP only
  * 20 MB max per file
  * 20 images max per project (video)
  * MIME + extension + magic-byte validation
  * sanitized, unique, user-isolated storage keys
  * no automatic compression
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select

from app.core.deps import CurrentUser, DbSession
from app.models import Asset, Video
from app.schemas.asset import AssetOut, AssetReorderRequest, AssetUpdateRequest
from app.storage import get_storage
from app.utils.uploads import (
    MAX_IMAGE_BYTES,
    MAX_IMAGES_PER_PROJECT,
    UploadValidationError,
    validate_image_upload,
)

log = logging.getLogger("hackroot.assets")

router = APIRouter(prefix="/assets", tags=["assets"])


async def _owned_video(db, user_id: int, video_id: int) -> Video:
    v = (await db.execute(
        select(Video).where(Video.id == video_id, Video.owner_id == user_id)
    )).scalar_one_or_none()
    if v is None:
        raise HTTPException(404, "Project (video) not found")
    return v


async def _project_image_count(db, user_id: int, video_id: int | None) -> int:
    stmt = select(func.count(Asset.id)).where(
        Asset.owner_id == user_id, Asset.kind == "image"
    )
    stmt = stmt.where(Asset.video_id == video_id) if video_id is not None else stmt.where(
        Asset.video_id.is_(None)
    )
    return (await db.execute(stmt)).scalar_one()


async def _next_sort_order(db, user_id: int, video_id: int | None) -> int:
    stmt = select(func.coalesce(func.max(Asset.sort_order), -1)).where(
        Asset.owner_id == user_id
    )
    stmt = stmt.where(Asset.video_id == video_id) if video_id is not None else stmt.where(
        Asset.video_id.is_(None)
    )
    return (await db.execute(stmt)).scalar_one() + 1


# ---------------------------------------------------------------------------
# Limits (used by the frontend to render client-side guards)
# ---------------------------------------------------------------------------
@router.get("/_limits")
async def limits() -> dict:
    return {
        "max_file_size_bytes": MAX_IMAGE_BYTES,
        "max_file_size_mb": MAX_IMAGE_BYTES // 1024 // 1024,
        "max_images_per_project": MAX_IMAGES_PER_PROJECT,
        "allowed_mime_types": ["image/jpeg", "image/png", "image/webp"],
        "allowed_extensions": [".jpg", ".jpeg", ".png", ".webp"],
        "compression": "none",
    }


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------
@router.post("/upload", response_model=AssetOut, status_code=201)
async def upload(
    user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
    video_id: int | None = Form(default=None),
    description: str | None = Form(default=None),
    kind: str = Form(default="image"),
) -> AssetOut:
    if kind not in ("image", "logo"):
        raise HTTPException(400, "kind must be 'image' or 'logo'")
    if video_id is not None:
        await _owned_video(db, user.id, video_id)

    raw = await file.read()
    try:
        img = validate_image_upload(
            data=raw, filename=file.filename, content_type=file.content_type
        )
    except UploadValidationError as e:
        raise HTTPException(e.status_code, e.message) from e
    finally:
        await file.close()

    if kind == "image":
        count = await _project_image_count(db, user.id, video_id)
        if count >= MAX_IMAGES_PER_PROJECT:
            raise HTTPException(
                409,
                f"Project already has {count} images — the limit is {MAX_IMAGES_PER_PROJECT}",
            )

    key = img.storage_key(user_id=user.id, prefix="logos" if kind == "logo" else "assets")
    path = get_storage().save_bytes(key, img.data)

    asset = Asset(
        owner_id=user.id,
        name=f"{img.base_name}{img.extension}",
        original_filename=img.original_filename,
        kind=kind,
        mime_type=img.mime_type,
        path=path,
        file_size_bytes=img.size_bytes,
        checksum=img.checksum,
        width=img.width,
        height=img.height,
        video_id=video_id,
        sort_order=await _next_sort_order(db, user.id, video_id),
        description=description,
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    log.info("User %s uploaded asset %s (%s bytes)", user.id, asset.id, asset.file_size_bytes)
    return AssetOut.model_validate(asset)


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------
@router.get("", response_model=list[AssetOut])
async def list_assets(
    user: CurrentUser,
    db: DbSession,
    video_id: int | None = None,
    kind: str | None = None,
) -> list[AssetOut]:
    stmt = select(Asset).where(Asset.owner_id == user.id)
    if video_id is not None:
        stmt = stmt.where(Asset.video_id == video_id)
    if kind is not None:
        stmt = stmt.where(Asset.kind == kind)
    stmt = stmt.order_by(Asset.sort_order.asc(), Asset.id.asc())
    res = await db.execute(stmt)
    return [AssetOut.model_validate(a) for a in res.scalars().all()]


@router.get("/{asset_id}", response_model=AssetOut)
async def get_asset(asset_id: int, user: CurrentUser, db: DbSession) -> AssetOut:
    a = (await db.execute(
        select(Asset).where(Asset.id == asset_id, Asset.owner_id == user.id)
    )).scalar_one_or_none()
    if a is None:
        raise HTTPException(404, "Asset not found")
    return AssetOut.model_validate(a)


@router.get("/{asset_id}/preview")
async def preview_asset(asset_id: int, user: CurrentUser, db: DbSession) -> FileResponse:
    """Auth-checked binary preview — works for both local and S3 backends."""
    a = (await db.execute(
        select(Asset).where(Asset.id == asset_id, Asset.owner_id == user.id)
    )).scalar_one_or_none()
    if a is None:
        raise HTTPException(404, "Asset not found")
    storage = get_storage()
    try:
        local_path = storage.open_path(a.path)
    except Exception as e:  # pragma: no cover - storage failure
        raise HTTPException(404, f"Asset file unavailable: {e}") from e
    return FileResponse(local_path, media_type=a.mime_type, filename=a.name)


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------
@router.patch("/{asset_id}", response_model=AssetOut)
async def update_asset(
    asset_id: int, payload: AssetUpdateRequest, user: CurrentUser, db: DbSession
) -> AssetOut:
    a = (await db.execute(
        select(Asset).where(Asset.id == asset_id, Asset.owner_id == user.id)
    )).scalar_one_or_none()
    if a is None:
        raise HTTPException(404, "Asset not found")
    data = payload.model_dump(exclude_unset=True)
    if "video_id" in data and data["video_id"] is not None:
        await _owned_video(db, user.id, data["video_id"])
    for k, v in data.items():
        setattr(a, k, v)
    await db.commit()
    await db.refresh(a)
    return AssetOut.model_validate(a)


@router.post("/reorder", response_model=list[AssetOut])
async def reorder_assets(
    payload: AssetReorderRequest, user: CurrentUser, db: DbSession
) -> list[AssetOut]:
    """Persist an explicit display/generation order for the given assets."""
    if len(set(payload.asset_ids)) != len(payload.asset_ids):
        raise HTTPException(400, "asset_ids contains duplicates")
    res = await db.execute(
        select(Asset).where(Asset.id.in_(payload.asset_ids), Asset.owner_id == user.id)
    )
    found = {a.id: a for a in res.scalars().all()}
    missing = [i for i in payload.asset_ids if i not in found]
    if missing:
        raise HTTPException(404, f"Assets not found or not owned by you: {missing}")
    for order, asset_id in enumerate(payload.asset_ids):
        found[asset_id].sort_order = order
    await db.commit()
    ordered = [found[i] for i in payload.asset_ids]
    for a in ordered:
        await db.refresh(a)
    return [AssetOut.model_validate(a) for a in ordered]


@router.delete("/{asset_id}", status_code=204)
async def delete_asset(asset_id: int, user: CurrentUser, db: DbSession):  # noqa: ANN201 — `-> None` breaks FastAPI 204 under future-annotations
    a = (await db.execute(
        select(Asset).where(Asset.id == asset_id, Asset.owner_id == user.id)
    )).scalar_one_or_none()
    if a is None:
        raise HTTPException(404, "Asset not found")
    try:
        get_storage().delete(a.path)
    except Exception as e:  # storage may already be gone; DB row must still go
        log.warning("Could not delete asset file %s: %s", a.path, e)
    await db.delete(a)
    await db.commit()

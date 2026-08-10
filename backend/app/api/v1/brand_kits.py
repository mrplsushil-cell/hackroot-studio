"""Brand kit routes."""
from __future__ import annotations
import os
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile
from sqlalchemy import select

from app.config import settings
from app.core.deps import CurrentUser, DbSession
from app.models import BrandKit
from app.schemas.brand_kit import BrandKitCreate, BrandKitOut, BrandKitUpdate
from app.storage import get_storage
from app.utils.files import safe_filename

router = APIRouter(prefix="/brand-kit", tags=["brand-kit"])


@router.get("", response_model=list[BrandKitOut])
async def list_kits(user: CurrentUser, db: DbSession) -> list[BrandKitOut]:
    res = await db.execute(
        select(BrandKit).where(BrandKit.owner_id == user.id).order_by(BrandKit.id.desc())
    )
    return [BrandKitOut.model_validate(b) for b in res.scalars().all()]


@router.post("", response_model=BrandKitOut, status_code=201)
async def create_kit(payload: BrandKitCreate, user: CurrentUser, db: DbSession) -> BrandKitOut:
    if payload.is_default:
        # Unset other defaults
        existing = (await db.execute(
            select(BrandKit).where(BrandKit.owner_id == user.id, BrandKit.is_default.is_(True))
        )).scalars().all()
        for b in existing:
            b.is_default = False
    b = BrandKit(owner_id=user.id, **payload.model_dump())
    db.add(b)
    await db.commit()
    await db.refresh(b)
    return BrandKitOut.model_validate(b)


@router.put("/{kit_id}", response_model=BrandKitOut)
async def update_kit(kit_id: int, payload: BrandKitUpdate, user: CurrentUser, db: DbSession) -> BrandKitOut:
    b = (await db.execute(
        select(BrandKit).where(BrandKit.id == kit_id, BrandKit.owner_id == user.id)
    )).scalar_one_or_none()
    if b is None:
        raise HTTPException(404, "Brand kit not found")
    # Only apply fields the client actually sent (exclude_unset avoids clobbering
    # unspecified fields with their schema defaults, e.g. name=None).
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(b, k, v)
    await db.commit()
    await db.refresh(b)
    return BrandKitOut.model_validate(b)


@router.delete("/{kit_id}", status_code=204)
async def delete_kit(kit_id: int, user: CurrentUser, db: DbSession):  # noqa: ANN201 — `-> None` breaks FastAPI 204 under future-annotations
    b = (await db.execute(
        select(BrandKit).where(BrandKit.id == kit_id, BrandKit.owner_id == user.id)
    )).scalar_one_or_none()
    if b is None:
        raise HTTPException(404, "Brand kit not found")
    await db.delete(b)
    await db.commit()


@router.post("/{kit_id}/default", response_model=BrandKitOut)
async def set_default_kit(kit_id: int, user: CurrentUser, db: DbSession) -> BrandKitOut:
    """Mark a brand kit as the user's default (unsetting any other default)."""
    b = (await db.execute(
        select(BrandKit).where(BrandKit.id == kit_id, BrandKit.owner_id == user.id)
    )).scalar_one_or_none()
    if b is None:
        raise HTTPException(404, "Brand kit not found")
    existing = (await db.execute(
        select(BrandKit).where(BrandKit.owner_id == user.id, BrandKit.is_default.is_(True))
    )).scalars().all()
    for other in existing:
        other.is_default = False
    b.is_default = True
    await db.commit()
    await db.refresh(b)
    return BrandKitOut.model_validate(b)


@router.post("/{kit_id}/logo", response_model=BrandKitOut)
async def upload_logo(
    kit_id: int, user: CurrentUser, db: DbSession, file: UploadFile = File(...)
) -> BrandKitOut:
    b = (await db.execute(
        select(BrandKit).where(BrandKit.id == kit_id, BrandKit.owner_id == user.id)
    )).scalar_one_or_none()
    if b is None:
        raise HTTPException(404, "Brand kit not found")
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "Logo must be an image")
    raw = await file.read()
    if len(raw) / 1024 / 1024 > settings.max_upload_size_mb:
        raise HTTPException(413, "Logo too large")
    ext = os.path.splitext(file.filename or "")[1].lower() or ".png"
    key = f"users/{user.id}/brand/{uuid.uuid4().hex}_logo{ext}"
    path = get_storage().save_bytes(key, raw)
    b.logo_path = path
    await db.commit()
    await db.refresh(b)
    return BrandKitOut.model_validate(b)

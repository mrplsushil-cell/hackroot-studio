"""Public REST API for Business-plan users.

Authenticated by API key (Authorization: Bearer <key> or ?api_key=).
Enforces monthly quota and per-key scopes. Credits are consumed like the
dashboard flow.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.models import ApiKey, User, Video, VideoJob, VideoJobStatus
from app.services.credits import can_generate

router = APIRouter(tags=["public-api"])


# ---------------------------------------------------------------------------
# API key auth
# ---------------------------------------------------------------------------
def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


async def get_api_key_user(
    authorization: str | None = Header(default=None),
    api_key: str | None = None,
    db: DbSession = None,
) -> tuple[ApiKey, User]:
    raw = None
    if authorization and authorization.lower().startswith("bearer "):
        raw = authorization.split(" ", 1)[1]
    elif api_key:
        raw = api_key
    if not raw:
        raise HTTPException(401, "API key required")
    prefix = raw[:8]
    digest = _hash_key(raw)
    res = await db.execute(
        select(ApiKey).where(ApiKey.key_prefix == prefix, ApiKey.key_hash == digest)
    )
    k = res.scalar_one_or_none()
    if not k or not k.is_active:
        raise HTTPException(401, "Invalid or inactive API key")
    if k.usage_count >= k.monthly_quota:
        raise HTTPException(429, "Monthly API quota exceeded")
    user = (await db.execute(select(User).where(User.id == k.user_id))).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(401, "User not found or inactive")
    return k, user


# ---------------------------------------------------------------------------
# Key management (user-authenticated)
# ---------------------------------------------------------------------------
class CreateKeyRequest(BaseModel):
    name: str
    scopes: str = "generate:video,generate:script,generate:thumbnail"
    monthly_quota: int = 1000


class ApiKeyOut(BaseModel):
    id: int
    name: str
    key_prefix: str
    scopes: str
    usage_count: int
    monthly_quota: int
    is_active: bool
    # only returned once, at creation
    full_key: str | None = None


@router.post("/api-keys", response_model=ApiKeyOut, status_code=status.HTTP_201_CREATED)
async def create_api_key(payload: CreateKeyRequest, user: CurrentUser, db: DbSession) -> ApiKeyOut:
    raw = "hk_" + uuid.uuid4().hex + uuid.uuid4().hex[:8]
    obj = ApiKey(
        user_id=user.id, name=payload.name, key_prefix=raw[:8],
        key_hash=hashlib.sha256(raw.encode()).hexdigest(),
        scopes=payload.scopes, monthly_quota=payload.monthly_quota,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return ApiKeyOut(
        id=obj.id, name=obj.name, key_prefix=obj.key_prefix, scopes=obj.scopes,
        usage_count=obj.usage_count, monthly_quota=obj.monthly_quota,
        is_active=obj.is_active, full_key=raw,  # returned ONCE
    )


@router.get("/api-keys", response_model=list[ApiKeyOut])
async def list_api_keys(user: CurrentUser, db: DbSession) -> list[ApiKeyOut]:
    res = await db.execute(select(ApiKey).where(ApiKey.user_id == user.id))
    return [
        ApiKeyOut(id=k.id, name=k.name, key_prefix=k.key_prefix, scopes=k.scopes,
                  usage_count=k.usage_count, monthly_quota=k.monthly_quota, is_active=k.is_active)
        for k in res.scalars().all()
    ]


# ---------------------------------------------------------------------------
# Public generation endpoints
# ---------------------------------------------------------------------------
class GenerateRequest(BaseModel):
    prompt: str
    duration: int = 15
    aspect_ratio: str = "9:16"
    language: str = "English"
    style: str = "Cinematic"
    voice: str = "female"


@router.post("/generate-video", status_code=status.HTTP_202_ACCEPTED)
async def generate_video(req: GenerateRequest, db: DbSession,
                         creds: tuple[ApiKey, User] = Depends(get_api_key_user)) -> dict:
    k, user = creds
    _scope_check(k, "generate:video")
    allowed, cost, reason = await can_generate(db, user, req.duration)
    if not allowed:
        raise HTTPException(402, {"error": "credits_exhausted", "message": reason})
    video = Video(owner_id=user.id, title=req.prompt[:60] or "API video",
                  prompt=req.prompt, duration=req.duration, aspect_ratio=req.aspect_ratio,
                  language=req.language, style=req.style, voice=req.voice)
    db.add(video)
    await db.commit()
    await db.refresh(video)
    # touch key usage
    k.usage_count += 1
    k.last_used_at = datetime.now(timezone.utc)
    await db.commit()
    return {"video_id": video.id, "cost_credits": cost, "status": "queued"}


@router.post("/script")
async def generate_script(req: GenerateRequest, db: DbSession,
                          creds: tuple[ApiKey, User] = Depends(get_api_key_user)) -> dict:
    k, user = creds
    _scope_check(k, "generate:script")
    k.usage_count += 1
    await db.commit()
    return {"script": f"[mock script] {req.prompt}", "language": req.language}


@router.post("/thumbnail")
async def generate_thumbnail(req: GenerateRequest, creds: tuple[ApiKey, User] = Depends(get_api_key_user)) -> dict:
    k, _ = creds
    _scope_check(k, "generate:thumbnail")
    k.usage_count += 1
    return {"thumbnail_url": f"https://cdn.hackroot.studio/thumb/{uuid.uuid4().hex}.jpg"}


def _scope_check(key: ApiKey, needed: str) -> None:
    scopes = key.scopes.split(",")
    if needed not in scopes:
        raise HTTPException(403, f"API key lacks scope: {needed}")


__all__ = ["router", "create_api_key", "ApiKeyOut", "CreateKeyRequest"]

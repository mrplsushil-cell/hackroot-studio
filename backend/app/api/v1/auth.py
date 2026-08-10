"""Auth routes."""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.core.security import (
    create_access_token, decode_access_token, hash_password, verify_password,
)
from app.models import User
from app.schemas.auth import Token, UserCreate, UserLogin, UserOut
from app.services import email_events

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: DbSession) -> Token:
    existing = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    # Fire-and-forget transactional emails (mock SMTP is safe + logged).
    email_events.send_welcome(user)
    email_events.send_verification(user, token=create_access_token(user.id))
    token = create_access_token(user.id)
    return Token(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=Token)
async def login(payload: UserLogin, db: DbSession) -> Token:
    res = await db.execute(select(User).where(User.email == payload.email))
    user = res.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")
    token = create_access_token(user.id)
    return Token(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.post("/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(payload: dict, db: DbSession) -> dict:
    """Request a password reset link. Always 202 to avoid user enumeration."""
    email = (payload or {}).get("email")
    if email:
        res = await db.execute(select(User).where(User.email == email))
        user = res.scalar_one_or_none()
        if user:
            email_events.send_password_reset(user, token=create_access_token(user.id, expires_delta=timedelta(minutes=30)))
    return {"detail": "If the account exists, a reset link has been sent."}


@router.post("/password-reset/confirm", status_code=status.HTTP_200_OK)
async def confirm_password_reset(payload: dict, db: DbSession) -> dict:
    token = (payload or {}).get("token")
    new_password = (payload or {}).get("password")
    if not token or not new_password:
        raise HTTPException(400, "token and password are required")
    from app.core.security import decode_access_token
    uid = decode_access_token(token)
    if uid is None:
        raise HTTPException(400, "Invalid or expired token")
    user_id = int(uid.get("sub")) if isinstance(uid, dict) else None
    if user_id is None:
        raise HTTPException(400, "Invalid or expired token")
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    user.hashed_password = hash_password(new_password)
    await db.commit()
    return {"detail": "Password updated."}

"""Team workspace (Business plan). Invite Owner/Admin/Editor/Viewer members."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.models import Subscription, SubscriptionPlan, TeamMember, User
from app.schemas.billing import PlanOut

router = APIRouter(prefix="/team", tags=["team"])


async def _require_business(db, user: User) -> None:
    res = await db.execute(
        select(Subscription).where(Subscription.user_id == user.id, Subscription.status == "active")
        .join(SubscriptionPlan, SubscriptionPlan.id == Subscription.plan_id)
    )
    sub = res.scalars().first()
    if not sub or not sub.plan.api_access:
        raise HTTPException(403, "Team workspace requires a Business plan")


@router.get("/members", response_model=list[dict])
async def list_members(user: CurrentUser, db: DbSession) -> list[dict]:
    await _require_business(db, user)
    res = await db.execute(select(TeamMember).where(TeamMember.owner_id == user.id))
    return [
        {"id": m.id, "email": m.email, "role": m.role, "status": m.status,
         "invited_at": m.invited_at, "accepted_at": m.accepted_at}
        for m in res.scalars().all()
    ]


@router.post("/invite", response_model=dict, status_code=201)
async def invite_member(email: str, role: str = "viewer", user: CurrentUser = None, db: DbSession = None) -> dict:
    await _require_business(db, user)
    if role not in ("owner", "admin", "editor", "viewer"):
        raise HTTPException(400, "Invalid role")
    existing = (await db.execute(
        select(TeamMember).where(TeamMember.owner_id == user.id, TeamMember.email == email)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(400, "Already invited")
    member = TeamMember(owner_id=user.id, email=email, role=role, status="invited")
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return {"id": member.id, "email": member.email, "role": member.role, "status": member.status}


@router.delete("/members/{mid}")
async def remove_member(mid: int, user: CurrentUser, db: DbSession) -> dict:
    await _require_business(db, user)
    m = (await db.execute(
        select(TeamMember).where(TeamMember.id == mid, TeamMember.owner_id == user.id)
    )).scalar_one_or_none()
    if not m:
        raise HTTPException(404, "Member not found")
    await db.delete(m)
    await db.commit()
    return {"ok": True}

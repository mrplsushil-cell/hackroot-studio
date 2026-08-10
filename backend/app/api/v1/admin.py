"""Admin / Owner dashboard API.

All routes require ``is_superuser``. Provides aggregated stats, lookups and
admin actions (adjust credits, toggle plans, view logs/analytics).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, DbSession
from app.models import (
    AuditLog, BrandKit, CreditTransaction, Invoice, RequestLog, Subscription,
    SubscriptionPlan, Template, User, Video,
)
from app.schemas.billing import PlanOut
from app.services.credits import grant_credits

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(user: CurrentUser) -> None:
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")


# ---------------------------------------------------------------------------
# Dashboard stats
# ---------------------------------------------------------------------------
@router.get("/stats")
async def admin_stats(user: CurrentUser, db: DbSession) -> dict:
    _require_admin(user)
    now = datetime.now(timezone.utc)
    month_start = now - timedelta(days=30)

    total_users = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    active_subs = (await db.execute(
        select(func.count()).select_from(Subscription).where(Subscription.status == "active")
    )).scalar_one()
    videos = (await db.execute(select(func.count()).select_from(Video))).scalar_one()
    videos_30 = (await db.execute(
        select(func.count()).select_from(Video).where(Video.created_at >= month_start)
    )).scalar_one()
    revenue = (await db.execute(
        select(func.coalesce(func.sum(Invoice.total_amount), 0))
        .select_from(Invoice).where(Invoice.status == "paid", Invoice.created_at >= month_start)
    )).scalar_one()
    new_users_30 = (await db.execute(
        select(func.count()).select_from(User).where(User.created_at >= month_start)
    )).scalar_one()
    credits_consumed = (await db.execute(
        select(func.coalesce(func.sum(CreditTransaction.change), 0))
        .select_from(CreditTransaction).where(CreditTransaction.change < 0)
    )).scalar_one()
    unpaid = (await db.execute(
        select(func.count()).select_from(Invoice).where(Invoice.status == "failed")
    )).scalar_one()

    return {
        "total_users": total_users,
        "active_subscriptions": active_subs,
        "total_videos": videos,
        "videos_last_30d": videos_30,
        "revenue_last_30d": int(revenue),
        "new_users_last_30d": new_users_30,
        "credits_consumed": abs(int(credits_consumed)),
        "failed_payments": unpaid,
    }


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
@router.get("/users")
async def list_users(user: CurrentUser, db: DbSession,
                     limit: int = Query(100, ge=1, le=500), q: str | None = None) -> list[dict]:
    _require_admin(user)
    stmt = select(User).order_by(User.created_at.desc()).limit(limit)
    if q:
        stmt = stmt.where(User.email.ilike(f"%{q}%"))
    res = await db.execute(stmt)
    return [
        {"id": u.id, "email": u.email, "full_name": u.full_name,
         "is_active": u.is_active, "is_superuser": u.is_superuser,
         "credits_total": u.credits_total, "credits_used": u.credits_used,
         "created_at": u.created_at}
        for u in res.scalars().all()
    ]


@router.post("/users/{uid}/credits")
async def adjust_credits(uid: int, amount: int, note: str | None = None,
                        user: CurrentUser = None, db: DbSession = None) -> dict:
    _require_admin(user)
    u = (await db.execute(select(User).where(User.id == uid))).scalar_one_or_none()
    if not u:
        raise HTTPException(404, "User not found")
    await grant_credits(db, u, amount, reason="admin_grant", admin_user_id=user.id,
                       note=note, commit=False)
    db.add(AuditLog(actor_id=user.id, actor_type="admin", action="adjust_credits",
                    target_type="user", target_id=uid, detail=f"amount={amount}"))
    await db.commit()
    return {"user_id": uid, "credits_total": u.credits_total, "credits_used": u.credits_used}


# ---------------------------------------------------------------------------
# Subscriptions / plans / invoices
# ---------------------------------------------------------------------------
@router.get("/subscriptions")
async def list_subscriptions(user: CurrentUser, db: DbSession,
                             limit: int = Query(100, ge=1, le=500)) -> list[dict]:
    _require_admin(user)
    res = await db.execute(
        select(Subscription).options(selectinload(Subscription.plan))
        .order_by(Subscription.created_at.desc()).limit(limit)
    )
    return [
        {"id": s.id, "user_id": s.user_id, "plan": s.plan.name if s.plan else None,
         "status": s.status, "billing_cycle": s.billing_cycle,
         "current_period_end": s.current_period_end}
        for s in res.scalars().all()
    ]


@router.get("/plans", response_model=list[PlanOut])
async def list_plans_admin(user: CurrentUser, db: DbSession) -> list[SubscriptionPlan]:
    _require_admin(user)
    res = await db.execute(select(SubscriptionPlan).order_by(SubscriptionPlan.sort_order.asc()))
    return list(res.scalars().all())


@router.patch("/plans/{pid}")
async def toggle_plan(pid: int, is_active: bool, user: CurrentUser, db: DbSession) -> dict:
    _require_admin(user)
    p = (await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.id == pid))).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Plan not found")
    p.is_active = is_active
    await db.commit()
    return {"id": p.id, "is_active": p.is_active}


@router.get("/invoices")
async def list_invoices_admin(user: CurrentUser, db: DbSession,
                              limit: int = Query(100, ge=1, le=500)) -> list[dict]:
    _require_admin(user)
    res = await db.execute(select(Invoice).order_by(Invoice.created_at.desc()).limit(limit))
    return [
        {"id": i.id, "invoice_no": i.invoice_no, "user_id": i.user_id,
         "amount": i.total_amount, "currency": i.currency, "status": i.status,
         "created_at": i.created_at}
        for i in res.scalars().all()
    ]


# ---------------------------------------------------------------------------
# Content overview
# ---------------------------------------------------------------------------
@router.get("/templates")
async def list_templates_admin(user: CurrentUser, db: DbSession,
                               limit: int = Query(100, ge=1, le=500)) -> list[dict]:
    _require_admin(user)
    res = await db.execute(select(Template).order_by(Template.id.desc()).limit(limit))
    return [{"id": t.id, "name": t.name, "category": t.category,
            "is_system": t.is_system, "is_active": t.is_active} for t in res.scalars().all()]


@router.get("/brand-kits")
async def list_brandkits_admin(user: CurrentUser, db: DbSession,
                               limit: int = Query(100, ge=1, le=500)) -> list[dict]:
    _require_admin(user)
    res = await db.execute(select(BrandKit).order_by(BrandKit.id.desc()).limit(limit))
    return [{"id": b.id, "name": b.name, "owner_id": b.owner_id,
            "is_default": b.is_default} for b in res.scalars().all()]


@router.get("/videos")
async def list_videos_admin(user: CurrentUser, db: DbSession,
                            limit: int = Query(100, ge=1, le=500)) -> list[dict]:
    _require_admin(user)
    res = await db.execute(select(Video).order_by(Video.created_at.desc()).limit(limit))
    return [{"id": v.id, "owner_id": v.owner_id, "title": v.title,
            "duration": v.duration, "status": v.status, "created_at": v.created_at}
           for v in res.scalars().all()]


# ---------------------------------------------------------------------------
# Logs & analytics
# ---------------------------------------------------------------------------
@router.get("/logs/requests")
async def request_logs(user: CurrentUser, db: DbSession,
                       limit: int = Query(200, ge=1, le=500)) -> list[dict]:
    _require_admin(user)
    res = await db.execute(select(RequestLog).order_by(RequestLog.created_at.desc()).limit(limit))
    return [
        {"id": r.id, "method": r.method, "path": r.path, "status_code": r.status_code,
         "user_id": r.user_id, "ip": r.ip, "created_at": r.created_at}
        for r in res.scalars().all()
    ]


@router.get("/audit-logs")
async def audit_logs(user: CurrentUser, db: DbSession,
                     limit: int = Query(200, ge=1, le=500)) -> list[dict]:
    _require_admin(user)
    res = await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit))
    return [
        {"id": a.id, "actor_id": a.actor_id, "action": a.action,
         "target_type": a.target_type, "detail": a.detail, "created_at": a.created_at}
        for a in res.scalars().all()
    ]


@router.get("/analytics")
async def analytics(user: CurrentUser, db: DbSession) -> dict:
    _require_admin(user)
    now = datetime.now(timezone.utc)
    # Daily revenue (last 14 days)
    daily = []
    for d in range(13, -1, -1):
        day = (now - timedelta(days=d)).date()
        start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        rev = (await db.execute(
            select(func.coalesce(func.sum(Invoice.total_amount), 0))
            .select_from(Invoice).where(
                Invoice.status == "paid", Invoice.created_at >= start, Invoice.created_at < end)
        )).scalar_one()
        daily.append({"date": str(day), "revenue": int(rev)})
    # Top plans by active subs
    top_plans = (await db.execute(
        select(SubscriptionPlan.name, func.count(Subscription.id))
        .join(Subscription, Subscription.plan_id == SubscriptionPlan.id)
        .where(Subscription.status == "active")
        .group_by(SubscriptionPlan.name)
    )).all()
    # Top templates by usage (videos referencing template_id)
    top_templates = (await db.execute(
        select(Template.name, func.count(Video.id))
        .join(Video, Video.template_id == Template.id)
        .group_by(Template.name).order_by(func.count(Video.id).desc()).limit(5)
    )).all()
    # Most active users (videos created)
    top_users = (await db.execute(
        select(User.email, func.count(Video.id))
        .join(Video, Video.owner_id == User.id)
        .group_by(User.email).order_by(func.count(Video.id).desc()).limit(5)
    )).all()
    return {
        "daily_revenue": daily,
        "top_plans": [{"name": n, "count": c} for n, c in top_plans],
        "top_templates": [{"name": n, "count": c} for n, c in top_templates],
        "top_users": [{"email": e, "count": c} for e, c in top_users],
        "active_users": (await db.execute(
            select(func.count(func.distinct(Video.owner_id)))
        )).scalar_one(),
    }

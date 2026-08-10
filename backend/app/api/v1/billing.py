"""Billing, subscription, invoices, credits and notifications API.

All money is stored in minor units (paise for INR). The Razorpay secret key is
NEVER returned. When no keys are configured the provider runs in mock mode so the
entire flow can be tested without real credentials.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.deps import CurrentUser, DbSession
from app.models import (
    CreditTransaction, Invoice, Notification, Subscription, SubscriptionPlan, User,
)
from app.providers.payments.razorpay import get_razorpay
from app.schemas.billing import (
    CheckoutRequest, CheckoutResponse, CreditTransactionOut, CurrentPlanOut,
    InvoiceOut, PaymentVerifyRequest, PlanOut, SubscriptionOut,
)
from app.services.credits import grant_credits, monthly_reset
from app.services.plans import FREE_SLUG

router = APIRouter(prefix="/billing", tags=["billing"])


# ---------------------------------------------------------------------------
# Plans & current plan
# ---------------------------------------------------------------------------
@router.get("/plans", response_model=list[PlanOut])
async def list_plans(db: DbSession) -> list[SubscriptionPlan]:
    res = await db.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.is_active.is_(True))
        .order_by(SubscriptionPlan.sort_order.asc())
    )
    return list(res.scalars().all())


@router.get("/current", response_model=CurrentPlanOut)
async def current_plan(user: CurrentUser, db: DbSession) -> CurrentPlanOut:
    sub = await _active_subscription(db, user.id)
    plan = sub.plan if sub else await _free_plan(db)
    return CurrentPlanOut(
        plan=PlanOut.model_validate(plan),
        subscription=SubscriptionOut.model_validate(sub) if sub else None,
        credits_total=user.credits_total,
        credits_used=user.credits_used,
        credits_remaining=max(0, user.credits_total - user.credits_used),
    )


# ---------------------------------------------------------------------------
# Checkout (create Razorpay order / subscription, or mock)
# ---------------------------------------------------------------------------
@router.post("/checkout", response_model=CheckoutResponse, status_code=status.HTTP_201_CREATED)
async def checkout(payload: CheckoutRequest, user: CurrentUser, db: DbSession) -> CheckoutResponse:
    plan = await _plan_by_slug(db, payload.plan_slug)
    if not plan:
        raise HTTPException(404, "Plan not found")
    if payload.billing_cycle not in ("monthly", "yearly"):
        raise HTTPException(400, "billing_cycle must be monthly or yearly")
    amount = plan.price_yearly if payload.billing_cycle == "yearly" else plan.price_monthly
    rz = get_razorpay()

    sub_id = None
    if rz.mock:
        order_id = f"order_{uuid.uuid4().hex[:16]}"
    elif plan.razorpay_plan_id and payload.billing_cycle == "monthly":
        # Recurring subscription
        sub = await rz.create_subscription(plan.razorpay_plan_id)
        sub_id = sub["id"]
        order_id = sub["id"]
    else:
        order = await rz.create_order(amount, plan.currency, f"sub_{user.id}_{plan.slug}")
        order_id = order["id"]

    return CheckoutResponse(
        order_id=order_id, amount=amount, currency=plan.currency,
        razorpay_key_id=rz.key_id if not rz.mock else None,
        subscription_id=sub_id, mock=rz.mock,
    )


# ---------------------------------------------------------------------------
# Verify payment & activate subscription
# ---------------------------------------------------------------------------
@router.post("/verify", response_model=SubscriptionOut, status_code=status.HTTP_201_CREATED)
async def verify_payment(payload: PaymentVerifyRequest, user: CurrentUser, db: DbSession) -> SubscriptionOut:
    plan = await _plan_by_slug(db, payload.plan_slug)
    if not plan:
        raise HTTPException(404, "Plan not found")
    rz = get_razorpay()

    # Verify signature (mock always passes)
    ok = True
    if not rz.mock:
        ok = rz.verify_payment_signature(
            payload.razorpay_order_id or "", payload.razorpay_payment_id or "",
            payload.razorpay_signature or "",
        )
    if not ok:
        raise HTTPException(400, "Payment signature verification failed")

    # Deactivate existing subs
    await _deactivate_active(db, user.id)

    now = datetime.now(timezone.utc)
    period_end = now + (timedelta(days=365) if payload.billing_cycle == "yearly" else timedelta(days=30))
    sub = Subscription(
        user_id=user.id, plan_id=plan.id, status="active",
        billing_cycle=payload.billing_cycle,
        current_period_start=now, current_period_end=period_end,
        razorpay_subscription_id=payload.razorpay_subscription_id,
        razorpay_customer_id=payload.razorpay_order_id,
        external_status="active" if rz.mock else "authenticated",
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)

    # Grant the plan's monthly credits (additive on top of remaining).
    await grant_credits(db, user, plan.credits_per_month, reason="purchase",
                       reference_type="subscription", reference_id=sub.id, commit=False)

    # Invoice
    amount = plan.price_yearly if payload.billing_cycle == "yearly" else plan.price_monthly
    inv = Invoice(
        invoice_no=_invoice_no(), user_id=user.id, subscription_id=sub.id,
        plan_id=plan.id, amount=amount, currency=plan.currency,
        total_amount=amount, status="paid", billing_cycle=payload.billing_cycle,
        paid_at=now, razorpay_order_id=payload.razorpay_order_id,
        razorpay_payment_id=payload.razorpay_payment_id,
        description=f"{plan.name} ({payload.billing_cycle})",
    )
    db.add(inv)
    db.add(Notification(
        user_id=user.id, type="subscription_activated",
        title="Subscription activated", body=f"You are now on the {plan.name} plan.",
        link="/billing",
    ))
    await db.commit()

    # Transactional emails (mock SMTP is safe + logged; never breaks the flow).
    from app.services import email_events
    email_events.send_payment_success(user, amount, plan.name)
    email_events.send_subscription_activated(user, plan.name)
    email_events.send_invoice_generated(user, inv.invoice_no, amount)

    # Refresh with plan loaded
    res = await db.execute(
        select(Subscription).where(Subscription.id == sub.id).options(selectinload(Subscription.plan))
    )
    return SubscriptionOut.model_validate(res.scalar_one())


# ---------------------------------------------------------------------------
# Cancel / change / renew
# ---------------------------------------------------------------------------
@router.post("/cancel", response_model=SubscriptionOut)
async def cancel_subscription(user: CurrentUser, db: DbSession) -> SubscriptionOut:
    sub = await _active_subscription(db, user.id)
    if not sub:
        raise HTTPException(404, "No active subscription")
    sub.cancel_at_period_end = True
    sub.external_status = "cancelled"
    db.add(Notification(
        user_id=user.id, type="subscription_expiring",
        title="Subscription set to cancel", body="Your plan will end at the current period.",
        link="/billing",
    ))
    await db.commit()
    return await _subscription_out(db, sub.id)


@router.post("/renew", response_model=SubscriptionOut)
async def renew_subscription(user: CurrentUser, db: DbSession) -> SubscriptionOut:
    sub = await _active_subscription(db, user.id)
    if not sub:
        raise HTTPException(404, "No active subscription")
    if not sub.cancel_at_period_end:
        raise HTTPException(400, "Subscription is already active")
    sub.cancel_at_period_end = False
    sub.external_status = "active"
    await db.commit()
    return await _subscription_out(db, sub.id)


@router.post("/change", response_model=SubscriptionOut, status_code=status.HTTP_201_CREATED)
async def change_plan(plan_slug: str, billing_cycle: str = "monthly",
                      user: CurrentUser = None, db: DbSession = None) -> SubscriptionOut:
    plan = await _plan_by_slug(db, plan_slug)
    if not plan:
        raise HTTPException(404, "Plan not found")
    await _deactivate_active(db, user.id)
    now = datetime.now(timezone.utc)
    period_end = now + (timedelta(days=365) if billing_cycle == "yearly" else timedelta(days=30))
    sub = Subscription(
        user_id=user.id, plan_id=plan.id, status="active", billing_cycle=billing_cycle,
        current_period_start=now, current_period_end=period_end, external_status="active",
    )
    db.add(sub)
    await grant_credits(db, user, plan.credits_per_month, reason="purchase",
                       reference_type="subscription", reference_id=sub.id, commit=False)
    await db.commit()
    return await _subscription_out(db, sub.id)


# ---------------------------------------------------------------------------
# Invoices & credit ledger
# ---------------------------------------------------------------------------
@router.get("/invoices", response_model=list[InvoiceOut])
async def list_invoices(user: CurrentUser, db: DbSession,
                        limit: int = Query(50, ge=1, le=200)) -> list[Invoice]:
    res = await db.execute(
        select(Invoice).where(Invoice.user_id == user.id)
        .order_by(Invoice.created_at.desc()).limit(limit)
    )
    return list(res.scalars().all())


@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
async def get_invoice(invoice_id: int, user: CurrentUser, db: DbSession) -> Invoice:
    inv = (await db.execute(
        select(Invoice).where(Invoice.id == invoice_id, Invoice.user_id == user.id)
    )).scalar_one_or_none()
    if not inv:
        raise HTTPException(404, "Invoice not found")
    return inv


@router.get("/credits/history", response_model=list[CreditTransactionOut])
async def credit_history(user: CurrentUser, db: DbSession,
                         limit: int = Query(50, ge=1, le=200)) -> list[CreditTransaction]:
    res = await db.execute(
        select(CreditTransaction).where(CreditTransaction.user_id == user.id)
        .order_by(CreditTransaction.created_at.desc()).limit(limit)
    )
    return list(res.scalars().all())


# ---------------------------------------------------------------------------
# Notifications (Notification Center)
# ---------------------------------------------------------------------------
@router.get("/notifications", response_model=list[dict])
async def list_notifications(user: CurrentUser, db: DbSession,
                             limit: int = Query(50, ge=1, le=200)) -> list[dict]:
    res = await db.execute(
        select(Notification).where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc()).limit(limit)
    )
    rows = res.scalars().all()
    return [
        {"id": n.id, "type": n.type, "title": n.title, "body": n.body,
         "link": n.link, "read": n.read, "created_at": n.created_at}
        for n in rows
    ]


@router.get("/notifications/unread-count", response_model=dict)
async def unread_count(user: CurrentUser, db: DbSession) -> dict:
    res = await db.execute(
        select(func.count()).select_from(Notification)
        .where(Notification.user_id == user.id, Notification.read.is_(False))
    )
    return {"unread": res.scalar_one()}


@router.post("/notifications/{nid}/read")
async def mark_read(nid: int, user: CurrentUser, db: DbSession) -> dict:
    n = (await db.execute(
        select(Notification).where(Notification.id == nid, Notification.user_id == user.id)
    )).scalar_one_or_none()
    if n:
        n.read = True
        await db.commit()
    return {"ok": True}


@router.post("/notifications/read-all")
async def mark_all_read(user: CurrentUser, db: DbSession) -> dict:
    res = await db.execute(
        select(Notification).where(Notification.user_id == user.id, Notification.read.is_(False))
    )
    for n in res.scalars().all():
        n.read = True
    await db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Webhook (Razorpay)
# ---------------------------------------------------------------------------
@router.post("/webhook/razorpay")
async def razorpay_webhook(request, db: DbSession) -> dict:  # noqa: ANN001
    body = await request.body()
    sig = request.headers.get("X-Razorpay-Signature", "")
    rz = get_razorpay()
    if not rz.mock and not rz.verify_webhook_signature(body, sig):
        raise HTTPException(400, "Invalid webhook signature")
    # In a full implementation we'd parse the event (payment.captured,
    # subscription.activated, etc.) and update invoices/subscriptions.
    return {"ok": True}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _plan_by_slug(db, slug: str) -> SubscriptionPlan | None:
    return (await db.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.slug == slug)
    )).scalar_one_or_none()


async def _free_plan(db) -> SubscriptionPlan:
    return (await db.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.slug == FREE_SLUG)
    )).scalar_one()


async def _active_subscription(db, user_id: int) -> Subscription | None:
    res = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user_id, Subscription.status == "active"
        ).options(selectinload(Subscription.plan))
        .order_by(Subscription.current_period_end.desc())
    )
    return res.scalars().first()


async def _deactivate_active(db, user_id: int) -> None:
    res = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user_id, Subscription.status == "active"
        )
    )
    for s in res.scalars().all():
        s.status = "expired"


async def _subscription_out(db, sub_id: int) -> SubscriptionOut:
    res = await db.execute(
        select(Subscription).where(Subscription.id == sub_id).options(selectinload(Subscription.plan))
    )
    return SubscriptionOut.model_validate(res.scalar_one())


def _invoice_no() -> str:
    return "INV-" + datetime.now(timezone.utc).strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:6].upper()

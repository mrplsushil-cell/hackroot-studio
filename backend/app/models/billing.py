"""SaaS monetization models: subscription plans, subscriptions, invoices, credits.
Production-grade enums and audit fields. PostgreSQL-friendly; SQLite-compatible
for tests via server_default func.now().
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SubscriptionPlan(Base):
    """A purchasable plan (Free / Starter / Pro / Business)."""

    __tablename__ = "subscription_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    slug: Mapped[str] = mapped_column(String(48), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(96), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_monthly: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # minor units (paise / cents)
    price_yearly: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="INR", nullable=False)
    credits_per_month: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    video_limit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0 = unlimited
    has_watermark: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priority_queue: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    api_access: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    team_members: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    razorpay_plan_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Subscription(Base):
    """A user's active (or past) subscription to a plan."""

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    plan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("subscription_plans.id"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(24), default="active", nullable=False, index=True)
    # active | trialing | past_due | cancelled | expired
    billing_cycle: Mapped[str] = mapped_column(String(12), default="monthly", nullable=False)
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    razorpay_subscription_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    razorpay_customer_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    external_status: Mapped[str | None] = mapped_column(String(48), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped[User] = relationship("User")  # type: ignore[name-defined]  # noqa: F821
    plan: Mapped[SubscriptionPlan] = relationship("SubscriptionPlan")  # noqa: F821


class Invoice(Base):
    """A billing invoice tied to a subscription payment or one-off charge."""

    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    invoice_no: Mapped[str] = mapped_column(String(48), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    subscription_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True
    )
    plan_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("subscription_plans.id"), nullable=True
    )
    amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="INR", nullable=False)
    tax_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="paid", nullable=False, index=True)
    # draft | pending | paid | failed | refunded | void
    billing_cycle: Mapped[str | None] = mapped_column(String(12), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    razorpay_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    razorpay_payment_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    razorpay_signature: Mapped[str | None] = mapped_column(String(256), nullable=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    receipt_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped[User] = relationship("User")  # type: ignore[name-defined]  # noqa: F821


class CreditTransaction(Base):
    """Append-only ledger of every credit change for a user."""

    __tablename__ = "credit_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    change: Mapped[int] = mapped_column(Integer, nullable=False)  # +bonus, -consumed
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # consume | monthly_reset | bonus | admin_grant | signup | refund | purchase
    reference_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reference_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    admin_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class Notification(Base):
    """In-app notification for the Notification Center."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # video_ready | credits_low | subscription_expiring | payment_failed | maintenance | generic
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    link: Mapped[str | None] = mapped_column(String(256), nullable=True)
    read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class ApiKey(Base):
    """Public REST API key for Business-plan users."""

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(96), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    key_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    scopes: Mapped[str] = mapped_column(String(128), default="generate:video,generate:script,generate:thumbnail", nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    monthly_quota: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class RequestLog(Base):
    """Lightweight audit/request log for the security dashboard."""

    __tablename__ = "request_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    api_key_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    method: Mapped[str] = mapped_column(String(8), nullable=False)
    path: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class TeamMember(Base):
    """Invited team member on a Business plan workspace."""

    __tablename__ = "team_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), default="viewer", nullable=False)
    # owner | admin | editor | viewer
    status: Mapped[str] = mapped_column(String(16), default="invited", nullable=False)
    # invited | active | revoked
    invited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    """Admin/security audit trail for sensitive actions."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    actor_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    actor_type: Mapped[str] = mapped_column(String(16), default="user", nullable=False)  # user | system | admin
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

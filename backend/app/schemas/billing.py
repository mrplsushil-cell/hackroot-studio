"""Billing / subscription / invoice schemas."""
from __future__ import annotations
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    slug: str
    name: str
    description: str | None
    price_monthly: int
    price_yearly: int
    currency: str
    credits_per_month: int
    video_limit: int
    has_watermark: bool
    priority_queue: bool
    api_access: bool
    team_members: int
    sort_order: int


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    plan_id: int
    status: str
    billing_cycle: str
    current_period_start: datetime | None
    current_period_end: datetime | None
    cancel_at_period_end: bool
    plan: PlanOut | None = None


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    invoice_no: str
    user_id: int
    subscription_id: int | None
    plan_id: int | None
    amount: int
    currency: str
    tax_amount: int
    total_amount: int
    status: str
    billing_cycle: str | None
    paid_at: datetime | None
    razorpay_order_id: str | None
    razorpay_payment_id: str | None
    description: str | None
    receipt_url: str | None
    created_at: datetime


class CreditTransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    change: int
    balance_after: int
    reason: str
    reference_type: str | None
    reference_id: int | None
    note: str | None
    created_at: datetime


class CurrentPlanOut(BaseModel):
    plan: PlanOut
    subscription: SubscriptionOut | None
    credits_total: int
    credits_used: int
    credits_remaining: int


class CheckoutRequest(BaseModel):
    plan_slug: str
    billing_cycle: str = "monthly"  # monthly | yearly


class CheckoutResponse(BaseModel):
    order_id: str
    amount: int
    currency: str
    razorpay_key_id: str | None
    subscription_id: str | None = None
    mock: bool


class PaymentVerifyRequest(BaseModel):
    razorpay_order_id: str | None = None
    razorpay_payment_id: str | None = None
    razorpay_signature: str | None = None
    razorpay_subscription_id: str | None = None
    plan_slug: str
    billing_cycle: str = "monthly"

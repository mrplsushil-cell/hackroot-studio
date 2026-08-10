"""Razorpay payment provider abstraction.

The secret key is read from the environment and NEVER returned by any API.
When keys are absent (development / mock), the provider runs in `mock` mode:
order/payment/subscription calls return deterministic fake objects and signature
verification always passes, so the full billing flow can be exercised end-to-end
without real credentials. This mirrors the existing provider abstraction in the app.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import uuid
from datetime import datetime, timedelta, timezone

import httpx

from app.config import settings


class RazorpayProvider:
    """Thin wrapper around Razorpay with a mock fallback."""

    def __init__(self) -> None:
        self.key_id = settings.razorpay_key_id
        self.key_secret = settings.razorpay_key_secret  # kept server-side only
        self.webhook_secret = settings.razorpay_webhook_secret
        self.mock = not (self.key_id and self.key_secret)

    # ------------------------------------------------------------------
    # Order (one-time charge, used for plan purchases / upgrades)
    # ------------------------------------------------------------------
    async def create_order(self, amount_paise: int, currency: str, receipt: str,
                           notes: dict | None = None) -> dict:
        if self.mock:
            return {
                "id": f"order_{uuid.uuid4().hex[:16]}",
                "entity": "order",
                "amount": amount_paise,
                "currency": currency,
                "receipt": receipt,
                "status": "created",
                "notes": notes or {},
                "mock": True,
            }
        async with httpx.AsyncClient() as c:
            r = await c.post(
                "https://api.razorpay.com/v1/orders",
                auth=(self.key_id, self.key_secret),
                json={"amount": amount_paise, "currency": currency,
                      "receipt": receipt, "notes": notes or {}},
                timeout=20,
            )
            r.raise_for_status()
            return r.json()

    # ------------------------------------------------------------------
    # Subscription (recurring)
    # ------------------------------------------------------------------
    async def create_subscription(self, plan_id: str, total_count: int = 12,
                                   notes: dict | None = None) -> dict:
        if self.mock:
            return {
                "id": f"sub_{uuid.uuid4().hex[:16]}",
                "entity": "subscription",
                "plan_id": plan_id,
                "status": "created",
                "current_start": int(datetime.now(timezone.utc).timestamp()),
                "current_end": int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp()),
                "notes": notes or {},
                "mock": True,
            }
        async with httpx.AsyncClient() as c:
            r = await c.post(
                "https://api.razorpay.com/v1/subscriptions",
                auth=(self.key_id, self.key_secret),
                json={"plan_id": plan_id, "total_count": total_count, "notes": notes or {}},
                timeout=20,
            )
            r.raise_for_status()
            return r.json()

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------
    def verify_payment_signature(self, order_id: str, payment_id: str,
                                 signature: str) -> bool:
        if self.mock:
            return True
        msg = f"{order_id}|{payment_id}"
        expected = hmac.new(
            self.key_secret.encode(), msg.encode(), hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        if self.mock:
            return True
        expected = hmac.new(
            self.webhook_secret.encode(), body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    # ------------------------------------------------------------------
    # Mock helpers used by the gateway when no keys are present
    # ------------------------------------------------------------------
    def fake_payment(self, order_id: str) -> dict:
        return {
            "id": f"pay_{uuid.uuid4().hex[:16]}",
            "order_id": order_id,
            "status": "captured",
            "method": "card",
            "amount": 0,
            "currency": "INR",
            "mock": True,
        }


def get_razorpay() -> RazorpayProvider:
    return RazorpayProvider()

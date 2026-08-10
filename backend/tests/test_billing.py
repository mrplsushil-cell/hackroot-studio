"""Tests for the SaaS billing / credit flow against the in-process SQLite app.

Exercises the real endpoints: plan seeding, mock Razorpay checkout+verify,
subscription activation, credit granting, invoices, and the credit formula.
"""
from __future__ import annotations

import pytest

API = "/api/v1"


def _seed_plans(client):
    r = client.get(f"{API}/billing/plans")
    if r.status_code == 200 and r.json():
        return
    raise AssertionError("plans not seeded at startup")


@pytest.mark.asyncio
async def test_credit_consumption():
    """Credit engine: grant, consume, overdraft, ledger integrity."""
    from app.database import AsyncSessionLocal, Base, engine
    from app.models import User
    from app.services.credits import consume_credits, grant_credits
    from sqlalchemy import select

    # Ensure tables exist in the test database.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        u = User(email="credit2@example.com", full_name="Credit",
                 hashed_password="hashed-seed-value")
        db.add(u); await db.commit(); await db.refresh(u)

        await grant_credits(db, u, 50, reason="seed")
        await db.commit()
        res = await db.execute(select(User).where(User.id == u.id))
        u = res.scalar_one()
        start_total = u.credits_total
        ok = await consume_credits(db, u, 20, reference_type="generation", reference_id=1)
        assert ok == 2  # 20s -> 2 credits
        await db.commit()
        res = await db.execute(select(User).where(User.id == u.id))
        u2 = res.scalar_one()
        assert u2.credits_total == start_total  # grant added 50; total unchanged by consume
        assert u2.credits_used == 2

        ok2 = False
        try:
            await consume_credits(db, u, 9999, reference_type="generation")
        except ValueError:
            ok2 = True  # correctly refused the overdraft
        assert ok2 is True
        await db.rollback()

    from app.services.credits import credits_for_duration
    assert credits_for_duration(10) == 1
    assert credits_for_duration(20) == 2
    assert credits_for_duration(30) == 3
    assert credits_for_duration(60) == 5
    assert credits_for_duration(120) == 20


def test_notifications_unread(client, auth):
    # Use a fresh, isolated user so we don't mutate the shared module auth state.
    import time as _t
    email = f"notify_{int(_t.time())}@example.com"
    pw = "Str0ngPassw0rd!"
    reg = client.post(f"/api/v1/auth/register",
                      json={"email": email, "password": pw, "full_name": "Notif"})
    assert reg.status_code == 201, reg.text
    tok = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {tok}"}
    API = "/api/v1"
    co = client.post(f"{API}/billing/checkout", json={"plan_slug": "starter", "billing_cycle": "monthly"},
                     headers=headers).json()
    client.post(f"{API}/billing/verify",
                json={"plan_slug": "starter", "billing_cycle": "monthly", "razorpay_order_id": co["order_id"],
                      "razorpay_payment_id": co["order_id"], "razorpay_signature": "mock"},
                headers=headers)
    notes = client.get(f"{API}/billing/notifications", headers=headers).json()
    assert any(n["type"] == "subscription_activated" for n in notes)
    unread = client.get(f"{API}/billing/notifications/unread-count", headers=headers).json()
    assert unread["unread"] >= 1


def test_plans_seeded(client, auth):
    r = client.get(f"{API}/billing/plans", headers=auth)
    assert r.status_code == 200
    slugs = {p["slug"] for p in r.json()}
    assert {"free", "starter", "pro", "business"} <= slugs


def test_current_plan_free(client, auth):
    r = client.get(f"{API}/billing/current", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["plan"]["slug"] == "free"
    assert body["credits_remaining"] == body["credits_total"] - body["credits_used"]


def test_checkout_and_verify_mock(client, auth):
    r = client.post(f"{API}/billing/checkout",
                    json={"plan_slug": "starter", "billing_cycle": "monthly"}, headers=auth)
    assert r.status_code == 201
    co = r.json()
    assert co["mock"] is True
    assert co["amount"] == 29900

    r = client.post(f"{API}/billing/verify",
                    json={"plan_slug": "starter", "billing_cycle": "monthly"}, headers=auth)
    assert r.status_code == 201
    sub = r.json()
    assert sub["status"] == "active"
    assert sub["plan"]["slug"] == "starter"

    r = client.get(f"{API}/billing/current", headers=auth)
    assert r.json()["plan"]["slug"] == "starter"

    r = client.get(f"{API}/billing/invoices", headers=auth)
    assert any(i["status"] == "paid" for i in r.json())


def test_notifications_center(client, auth):
    r = client.get(f"{API}/billing/notifications", headers=auth)
    assert r.status_code == 200
    # After subscribing we should have a subscription_activated notification
    types = {n["type"] for n in r.json()}
    assert "subscription_activated" in types


def test_credit_history_recorded(client, auth):
    # Self-contained: ensure a purchase transaction exists before asserting.
    client.post(
        f"{API}/billing/checkout",
        headers=auth,
        json={"plan_slug": "starter", "billing_cycle": "monthly"},
    )
    client.post(
        f"{API}/billing/verify",
        headers=auth,
        json={
            "plan_slug": "starter",
            "billing_cycle": "monthly",
            "razorpay_order_id": "order_audit",
            "razorpay_payment_id": "order_audit",
            "razorpay_signature": "mock",
        },
    )
    r = client.get(f"{API}/billing/credits/history", headers=auth)
    assert r.status_code == 200
    reasons = {c["reason"] for c in r.json()}
    assert "purchase" in reasons

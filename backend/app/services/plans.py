"""Subscription plan definitions and credit-cost rules.

Kept as constants (not hardcoded in views) so the credit engine, billing
endpoints, and seeder all share one source of truth.
"""
from __future__ import annotations

# Credit cost for a generation, as a function of requested duration (seconds).
# Bands per spec: 10s=1, 20s=2, 30s=3, 60s=5.
def credits_for_duration(duration_seconds: int) -> int:
    d = max(5, int(duration_seconds))
    if d <= 10:
        return 1
    if d <= 20:
        return 2
    if d <= 30:
        return 3
    if d <= 60:
        return 5
    # beyond 60s: 5 credits per 30s block (rounded up)
    return 5 * ((d + 29) // 30)


# Plan catalogue. prices in minor units (paise for INR).
PLANS = [
    {
        "slug": "free", "name": "Free", "description": "Get started — 2 videos a month with a watermark.",
        "price_monthly": 0, "price_yearly": 0, "currency": "INR",
        "credits_per_month": 2, "video_limit": 2, "has_watermark": True,
        "priority_queue": False, "api_access": False, "team_members": 1, "sort_order": 0,
    },
    {
        "slug": "starter", "name": "Starter", "description": "For creators shipping regularly. No watermark.",
        "price_monthly": 29900, "price_yearly": 299000, "currency": "INR",
        "credits_per_month": 25, "video_limit": 25, "has_watermark": False,
        "priority_queue": False, "api_access": False, "team_members": 1, "sort_order": 1,
    },
    {
        "slug": "pro", "name": "Pro", "description": "Power users who need speed and priority rendering.",
        "price_monthly": 99900, "price_yearly": 999000, "currency": "INR",
        "credits_per_month": 150, "video_limit": 150, "has_watermark": False,
        "priority_queue": True, "api_access": False, "team_members": 1, "sort_order": 2,
    },
    {
        "slug": "business", "name": "Business", "description": "Teams with API access, members and priority support.",
        "price_monthly": 299900, "price_yearly": 2999000, "currency": "INR",
        "credits_per_month": 9999, "video_limit": 0, "has_watermark": False,
        "priority_queue": True, "api_access": True, "team_members": 10, "sort_order": 3,
    },
]

FREE_SLUG = "free"

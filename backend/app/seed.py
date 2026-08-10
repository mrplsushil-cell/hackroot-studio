"""Seed system templates, subscription plans and any other reference data."""
from __future__ import annotations
import json
import logging
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import SubscriptionPlan, Template
from app.services.plans import PLANS

log = logging.getLogger("hackroot.seed")

_TEMPLATES = [
    {
        "slug": "product-advertisement",
        "name": "Product Advertisement",
        "description": "High-converting product ads for social platforms.",
        "category": "Marketing", "icon": "shopping-bag",
        "default_duration": 20, "default_aspect_ratio": "9:16",
        "default_style": "Product Advertisement", "default_voice": "female",
        "default_language": "English", "scene_count": 4,
        "scene_blueprint": json.dumps([
            {"beat": "Hook"}, {"beat": "Showcase"},
            {"beat": "Features"}, {"beat": "Call to Action"},
        ]),
        "cta_template": "Order now 👇",
        "caption_style": "bold-center",
    },
    {
        "slug": "fashion-reel",
        "name": "Fashion Reel",
        "description": "Trendy vertical fashion reel with bold typography.",
        "category": "Fashion", "icon": "sparkles",
        "default_duration": 15, "default_aspect_ratio": "9:16",
        "default_style": "Fashion", "default_voice": "female",
        "default_language": "English", "scene_count": 4,
        "scene_blueprint": json.dumps([
            {"beat": "Hook"}, {"beat": "Showcase"},
            {"beat": "Detail"}, {"beat": "Call to Action"},
        ]),
        "cta_template": "Shop the look",
        "caption_style": "minimal",
    },
    {
        "slug": "product-launch",
        "name": "Product Launch",
        "description": "Cinematic reveal for a new product.",
        "category": "Marketing", "icon": "rocket",
        "default_duration": 30, "default_aspect_ratio": "16:9",
        "default_style": "Cinematic", "default_voice": "male",
        "default_language": "English", "scene_count": 4,
        "scene_blueprint": json.dumps([
            {"beat": "Hook"}, {"beat": "Reveal"},
            {"beat": "Features"}, {"beat": "Call to Action"},
        ]),
        "cta_template": "Available now",
        "caption_style": "lower-third",
    },
    {
        "slug": "instagram-reel",
        "name": "Instagram Reel",
        "description": "Quick hook + payoff format for Instagram.",
        "category": "Social", "icon": "instagram",
        "default_duration": 15, "default_aspect_ratio": "9:16",
        "default_style": "Social Media Reel", "default_voice": "female",
        "default_language": "Hinglish", "scene_count": 3,
        "scene_blueprint": json.dumps([
            {"beat": "Hook"}, {"beat": "Showcase"},
            {"beat": "Call to Action"},
        ]),
        "cta_template": "Save & share",
        "caption_style": "bold-center",
    },
    {
        "slug": "youtube-short",
        "name": "YouTube Short",
        "description": "Vertical short optimised for YouTube.",
        "category": "Social", "icon": "youtube",
        "default_duration": 30, "default_aspect_ratio": "9:16",
        "default_style": "Storytelling", "default_voice": "male",
        "default_language": "English", "scene_count": 4,
        "scene_blueprint": json.dumps([
            {"beat": "Hook"}, {"beat": "Setup"},
            {"beat": "Payoff"}, {"beat": "Call to Action"},
        ]),
        "cta_template": "Subscribe for more",
        "caption_style": "lower-third",
    },
    {
        "slug": "corporate-video",
        "name": "Corporate Video",
        "description": "Polished, brand-safe corporate intro.",
        "category": "Corporate", "icon": "building",
        "default_duration": 30, "default_aspect_ratio": "16:9",
        "default_style": "Corporate", "default_voice": "male",
        "default_language": "English", "scene_count": 4,
        "scene_blueprint": json.dumps([
            {"beat": "Hook"}, {"beat": "Mission"},
            {"beat": "Proof"}, {"beat": "Call to Action"},
        ]),
        "cta_template": "Learn more",
        "caption_style": "lower-third",
    },
    {
        "slug": "promotional-offer",
        "name": "Promotional Offer",
        "description": "Sale / discount announcement.",
        "category": "Marketing", "icon": "tag",
        "default_duration": 15, "default_aspect_ratio": "9:16",
        "default_style": "Product Advertisement", "default_voice": "female",
        "default_language": "English", "scene_count": 3,
        "scene_blueprint": json.dumps([
            {"beat": "Hook"}, {"beat": "Offer"},
            {"beat": "Call to Action"},
        ]),
        "cta_template": "Limited time only",
        "caption_style": "bold-center",
    },
    {
        "slug": "brand-story",
        "name": "Brand Story",
        "description": "Emotional storytelling format for your brand.",
        "category": "Branding", "icon": "book",
        "default_duration": 60, "default_aspect_ratio": "16:9",
        "default_style": "Storytelling", "default_voice": "female",
        "default_language": "English", "scene_count": 5,
        "scene_blueprint": json.dumps([
            {"beat": "Hook"}, {"beat": "Origin"},
            {"beat": "Values"}, {"beat": "Proof"},
            {"beat": "Call to Action"},
        ]),
        "cta_template": "Join the journey",
        "caption_style": "lower-third",
    },
]


async def seed_system_data() -> None:
    async with AsyncSessionLocal() as db:
        existing = (await db.execute(select(Template).where(Template.is_system.is_(True)))).scalars().all()
        existing_slugs = {t.slug for t in existing}
        added = 0
        for t in _TEMPLATES:
            if t["slug"] in existing_slugs:
                continue
            db.add(Template(**t, is_system=True, is_active=True))
            added += 1
        if added:
            await db.commit()
            log.info("Seeded %d system templates", added)

        # Subscription plans
        plan_rows = (await db.execute(select(SubscriptionPlan))).scalars().all()
        plan_slugs = {p.slug for p in plan_rows}
        p_added = 0
        for p in PLANS:
            if p["slug"] in plan_slugs:
                continue
            db.add(SubscriptionPlan(**p))
            p_added += 1
        if p_added:
            await db.commit()
            log.info("Seeded %d subscription plans", p_added)

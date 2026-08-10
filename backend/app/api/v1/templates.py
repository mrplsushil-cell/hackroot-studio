"""Templates routes."""
from __future__ import annotations
import json
import re
import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.models import Template
from app.schemas.template import TemplateCreate, TemplateOut

router = APIRouter(prefix="/templates", tags=["templates"])


def _slugify(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "template"
    return f"custom-{base}-{uuid.uuid4().hex[:6]}"


@router.get("", response_model=list[TemplateOut])
async def list_templates(db: DbSession, category: str | None = None) -> list[TemplateOut]:
    q = select(Template).where(Template.is_active.is_(True))
    if category:
        q = q.where(Template.category == category)
    q = q.order_by(Template.is_system.desc(), Template.id.asc())
    res = await db.execute(q)
    return [TemplateOut.model_validate(t) for t in res.scalars().all()]


@router.post("", response_model=TemplateOut, status_code=201)
async def create_template(payload: TemplateCreate, user: CurrentUser, db: DbSession) -> TemplateOut:
    """Create a user-defined custom template."""
    if not payload.scene_blueprint or not payload.scene_blueprint.strip():
        raise HTTPException(400, "scene_blueprint is required")
    try:
        parsed = json.loads(payload.scene_blueprint)
        if not isinstance(parsed, list) or not parsed:
            raise HTTPException(400, "scene_blueprint must be a non-empty JSON array")
    except json.JSONDecodeError:
        raise HTTPException(400, "scene_blueprint must be valid JSON")

    t = Template(
        slug=_slugify(payload.name),
        name=payload.name,
        description=payload.description,
        category=payload.category or "Custom",
        icon="sparkles",
        default_duration=payload.default_duration,
        default_aspect_ratio=payload.default_aspect_ratio,
        default_style=payload.default_style,
        default_voice=payload.default_voice,
        default_language=payload.default_language,
        scene_count=len(parsed),
        scene_blueprint=payload.scene_blueprint,
        cta_template=payload.cta_template,
        caption_style=payload.caption_style,
        is_active=True,
        is_system=False,
    )
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return TemplateOut.model_validate(t)


@router.get("/{template_id}", response_model=TemplateOut)
async def get_template(template_id: int, db: DbSession) -> TemplateOut:
    t = (await db.execute(select(Template).where(Template.id == template_id))).scalar_one_or_none()
    if t is None:
        raise HTTPException(404, "Template not found")
    return TemplateOut.model_validate(t)

"""API v1 router aggregation."""
from fastapi import APIRouter

from app.api.v1 import (
    admin, assets, auth, billing, brand_kits, providers, public_api, settings,
    team, templates, videos,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(videos.router)
api_router.include_router(assets.router)
api_router.include_router(templates.router)
api_router.include_router(brand_kits.router)
api_router.include_router(providers.router)
api_router.include_router(providers.agents_router)
api_router.include_router(settings.router)
api_router.include_router(billing.router)
api_router.include_router(team.router)
api_router.include_router(admin.router)
# Public API — mounted WITHOUT the /api/v1 double prefix (it re-declares it).
api_router.include_router(public_api.router)

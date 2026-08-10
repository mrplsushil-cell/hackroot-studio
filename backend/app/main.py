"""Hackroot Studio — FastAPI application entry point."""
from __future__ import annotations
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi import Request
from contextlib import asynccontextmanager

from app.api.v1.router import api_router
from app.config import settings
from app.database import init_db
from app.storage import get_storage

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("hackroot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Hackroot Studio starting (env=%s)", settings.app_env)
    # Ensure storage root exists
    try:
        get_storage()
    except Exception as e:
        log.warning("Storage init warning: %s", e)
    # In dev, ensure tables exist (alembic is the source of truth in prod)
    if settings.app_env == "development":
        try:
            await init_db()
        except Exception as e:
            log.warning("init_db skipped: %s", e)
    # Seed system templates
    try:
        from app.seed import seed_system_data
        await seed_system_data()
    except Exception as e:
        log.warning("seed skipped: %s", e)
    yield
    log.info("Hackroot Studio shutting down")


app = FastAPI(
    title="Hackroot Studio API",
    description="AI-powered video generation platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting + request logging (lightweight in-memory token bucket per IP).
import time
from collections import defaultdict, deque

_RATE: dict[str, deque] = defaultdict(deque)


@app.middleware("http")
async def rate_limit_and_log(request: Request, call_next):  # noqa: ANN001
    from app.models import ApiKey, RequestLog, User
    from sqlalchemy import select as _select
    from app.database import AsyncSessionLocal as _Session

    # Rate limiting + audit logging are production controls. In dev/test we pass
    # through to keep test suites fast and avoid per-request DB writes.
    if settings.app_env != "production":
        response = await call_next(request)
        return response

    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = _RATE[client_ip]
    while window and now - window[0] > 60:
        window.popleft()
    limit = settings.rate_limit_per_minute
    if len(window) >= limit:
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
    window.append(now)

    start = time.time()
    response = await call_next(request)
    latency = int((time.time() - start) * 1000)

    # Best-effort audit log (don't block the response).
    try:
        auth = request.headers.get("Authorization", "")
        uid = None
        if auth.lower().startswith("bearer "):
            from app.core.security import decode_access_token
            try:
                payload = decode_access_token(auth.split(" ", 1)[1])
                uid = int(payload["sub"]) if payload and "sub" in payload else None
            except Exception:
                uid = None
        async with _Session() as db:
            db.add(RequestLog(
                user_id=uid, method=request.method, path=request.url.path,
                status_code=response.status_code, ip=client_ip, latency_ms=latency,
            ))
            await db.commit()
    except Exception:  # noqa: BLE001
        pass
    return response

# Mount media (only for local storage)
try:
    from pathlib import Path
    media_root = Path(settings.storage_local_root)
    media_root.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=str(media_root)), name="media")
except Exception as e:
    log.warning("Could not mount /media: %s", e)


@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {"ok": True, "app": settings.app_name, "env": settings.app_env}


@app.get("/", tags=["meta"])
async def root() -> dict:
    return {
        "name": settings.app_name,
        "tagline": "Create. Imagine. Generate.",
        "docs": "/docs",
        "api": "/api/v1",
        "health": "/health",
    }


app.include_router(api_router)


@app.exception_handler(Exception)
async def unhandled_exception(request, exc):  # noqa: ANN001
    log.exception("Unhandled error")
    if settings.app_debug:
        return JSONResponse(status_code=500, content={"detail": str(exc), "type": type(exc).__name__})
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

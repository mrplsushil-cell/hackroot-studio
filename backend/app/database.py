"""Async SQLAlchemy database setup."""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    """Base for all ORM models."""


def _engine_kwargs() -> dict:
    """Pool options are dialect-specific — SQLite (tests) rejects pool sizing."""
    kwargs: dict = {"echo": settings.app_debug, "pool_pre_ping": True}
    if not settings.database_url.startswith("sqlite"):
        kwargs.update(pool_size=10, max_overflow=20)
    return kwargs


engine = create_async_engine(settings.async_database_url, **_engine_kwargs())

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create tables. Migrations are preferred; this is a safety net for tests."""
    from app import models  # noqa: F401 — register models

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

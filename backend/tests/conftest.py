"""Pytest configuration for the Hackroot Studio backend test suite.

Provides a shared in-process SQLite ``client`` + ``auth`` fixture used by all
HTTP-level tests. DB + storage are created fresh in a temp dir per session.
"""
import os
import sys
import tempfile
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

TMP_ROOT = tempfile.mkdtemp(prefix="hackroot_test_")
os.environ.setdefault("APP_ENV", "test")
os.environ["STORAGE_LOCAL_ROOT"] = TMP_ROOT
os.environ["STORAGE_PUBLIC_BASE_URL"] = "http://testserver/media"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + os.path.join(TMP_ROOT, "test.db").replace("\\", "/")

import pytest  # noqa: E402

pytest.importorskip("aiosqlite", reason="aiosqlite required for API tests")
pytest.importorskip("httpx", reason="httpx required for API tests")

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.storage.factory import get_storage  # noqa: E402

get_settings.cache_clear()
get_storage.cache_clear()


def png_bytes(size: tuple[int, int] = (80, 60), color=(200, 30, 90)) -> bytes:
    from io import BytesIO
    buf = BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture(scope="module")
def client():
    import asyncio

    async def _create() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_create())
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def auth(client) -> dict:
    payload = {"email": "qa@hackroot-qa.example.com", "password": "Str0ngPassw0rd!", "full_name": "QA User"}
    r = client.post("/api/v1/auth/register", json=payload)
    if r.status_code >= 400:
        r = client.post("/api/v1/auth/login", json={"email": payload["email"], "password": payload["password"]})
    assert r.status_code < 400, r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

"""End-to-end API tests for the Phase 3 asset manager.

Runs the real FastAPI app against an in-process SQLite database and a
temporary storage root, so upload -> list -> preview -> reorder -> delete is
exercised through the actual HTTP routes. Fixtures (client/auth) come from
conftest.py.
"""
from __future__ import annotations

import os

from io import BytesIO

import pytest

pytest.importorskip("aiosqlite", reason="aiosqlite required for API tests")
pytest.importorskip("httpx", reason="httpx required for API tests")
pytest.importorskip("PIL", reason="Pillow required for API tests")

from PIL import Image  # noqa: E402

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()


def png_bytes(size: tuple[int, int] = (80, 60), color=(200, 30, 90)) -> bytes:
    buf = BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def upload(client, auth, name="a.png", data=None, ctype="image/png", **form):
    return client.post(
        "/api/v1/assets/upload",
        headers=auth,
        files={"file": (name, data if data is not None else png_bytes(), ctype)},
        data=form or None,
    )


# ---------------------------------------------------------------------------
def test_limits_endpoint(client, auth):
    r = client.get("/api/v1/assets/_limits", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["max_file_size_mb"] == 20
    assert body["max_images_per_project"] == 20
    assert body["compression"] == "none"
    assert set(body["allowed_extensions"]) == {".jpg", ".jpeg", ".png", ".webp"}


def test_upload_requires_auth(client):
    r = upload(client, {})
    assert r.status_code == 401


def test_upload_and_metadata(client, auth):
    data = png_bytes((123, 45))
    r = upload(client, auth, name="My Product Shot.png", data=data)
    assert r.status_code == 201, r.text
    a = r.json()
    assert a["mime_type"] == "image/png"
    assert a["width"] == 123 and a["height"] == 45
    assert a["file_size_bytes"] == len(data), "stored size must equal source size (no compression)"
    assert a["original_filename"] == "My Product Shot.png"
    assert " " not in a["name"]
    assert a["url"].startswith("http")


def test_stored_bytes_are_identical(client, auth):
    data = png_bytes((70, 70), (1, 2, 3))
    aid = upload(client, auth, name="verbatim.png", data=data).json()["id"]
    r = client.get(f"/api/v1/assets/{aid}/preview", headers=auth)
    assert r.status_code == 200
    assert r.content == data, "preview bytes must be byte-identical to the upload"


def test_rejects_bad_type(client, auth):
    r = upload(client, auth, name="doc.pdf", data=b"%PDF-1.4 fake", ctype="application/pdf")
    assert r.status_code == 415


def test_rejects_spoofed_content(client, auth):
    buf = BytesIO()
    Image.new("RGB", (10, 10)).save(buf, format="JPEG")
    r = upload(client, auth, name="fake.png", data=buf.getvalue(), ctype="image/png")
    assert r.status_code == 400


def test_user_isolation(client, auth):
    """A second user must not see or touch the first user's assets."""
    other = {"email": "intruder@hackroot-qa.example.com", "password": "An0therPass!", "full_name": "Intruder"}
    reg = client.post("/api/v1/auth/register", json=other)
    if reg.status_code >= 400:
        reg = client.post("/api/v1/auth/login", json={"email": other["email"], "password": other["password"]})
    hdr = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    victim_id = upload(client, auth, name="private.png").json()["id"]
    assert client.get(f"/api/v1/assets/{victim_id}", headers=hdr).status_code == 404
    assert client.get(f"/api/v1/assets/{victim_id}/preview", headers=hdr).status_code == 404
    assert client.delete(f"/api/v1/assets/{victim_id}", headers=hdr).status_code == 404
    assert client.get("/api/v1/assets", headers=hdr).json() == []


def test_reorder_and_delete(client, auth):
    ids = [upload(client, auth, name=f"r{i}.png").json()["id"] for i in range(3)]
    reversed_ids = list(reversed(ids))

    r = client.post("/api/v1/assets/reorder", headers=auth, json={"asset_ids": reversed_ids})
    assert r.status_code == 200
    assert [a["id"] for a in r.json()] == reversed_ids
    assert [a["sort_order"] for a in r.json()] == [0, 1, 2]

    listed = [a["id"] for a in client.get("/api/v1/assets", headers=auth).json()]
    positions = [listed.index(i) for i in reversed_ids]
    assert positions == sorted(positions), "listing must honour persisted sort_order"

    assert client.delete(f"/api/v1/assets/{ids[0]}", headers=auth).status_code == 204
    assert client.get(f"/api/v1/assets/{ids[0]}", headers=auth).status_code == 404


def test_reorder_rejects_foreign_ids(client, auth):
    r = client.post("/api/v1/assets/reorder", headers=auth, json={"asset_ids": [999_999]})
    assert r.status_code == 404


def test_project_scoping_and_image_cap(client, auth):
    video = client.post(
        "/api/v1/videos",
        headers=auth,
        json={"prompt": "A cinematic ad for a coffee brand", "duration": 15},
    )
    assert video.status_code == 201, video.text
    vid = video.json()["id"]

    for i in range(20):
        r = upload(client, auth, name=f"p{i}.png", video_id=str(vid))
        assert r.status_code == 201, f"upload {i} failed: {r.text}"

    overflow = upload(client, auth, name="p20.png", video_id=str(vid))
    assert overflow.status_code == 409
    assert "20" in overflow.json()["detail"]

    scoped = client.get(f"/api/v1/assets?video_id={vid}", headers=auth).json()
    assert len(scoped) == 20
    assert [a["sort_order"] for a in scoped] == sorted(a["sort_order"] for a in scoped)


def test_attach_assets_to_video_on_create(client, auth):
    a1 = upload(client, auth, name="att1.png").json()["id"]
    a2 = upload(client, auth, name="att2.png").json()["id"]
    r = client.post(
        "/api/v1/videos",
        headers=auth,
        json={"prompt": "Attach the product images please", "asset_ids": [a2, a1]},
    )
    assert r.status_code == 201, r.text
    vid = r.json()["id"]
    scoped = client.get(f"/api/v1/assets?video_id={vid}", headers=auth).json()
    assert [a["id"] for a in scoped] == [a2, a1], "attachment order must be preserved"


def test_attach_rejects_unowned_asset(client, auth):
    r = client.post(
        "/api/v1/videos",
        headers=auth,
        json={"prompt": "Try to steal an asset", "asset_ids": [888_888]},
    )
    assert r.status_code == 404

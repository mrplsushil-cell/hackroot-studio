"""Tests for the Phase 3 image upload contract."""
from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

from app.utils.uploads import (
    ALLOWED_IMAGE_EXTENSIONS,
    MAX_IMAGE_BYTES,
    MAX_IMAGES_PER_PROJECT,
    UploadValidationError,
    validate_image_upload,
)


def make_image(fmt: str = "PNG", size: tuple[int, int] = (64, 48)) -> bytes:
    buf = BytesIO()
    Image.new("RGB", size, (10, 120, 200)).save(buf, format=fmt)
    return buf.getvalue()


# --------------------------------------------------------------------------
# Limits
# --------------------------------------------------------------------------
def test_limits_match_spec():
    assert MAX_IMAGE_BYTES == 20 * 1024 * 1024
    assert MAX_IMAGES_PER_PROJECT == 20
    assert ALLOWED_IMAGE_EXTENSIONS == {".jpg", ".jpeg", ".png", ".webp"}


# --------------------------------------------------------------------------
# Happy paths
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("fmt", "filename", "content_type", "mime"),
    [
        ("PNG", "shot.png", "image/png", "image/png"),
        ("JPEG", "shot.jpg", "image/jpeg", "image/jpeg"),
        ("JPEG", "shot.jpeg", "image/jpeg", "image/jpeg"),
        ("JPEG", "shot.jpg", "image/jpg", "image/jpeg"),  # non-standard alias
        ("WEBP", "shot.webp", "image/webp", "image/webp"),
    ],
)
def test_accepts_supported_formats(fmt, filename, content_type, mime):
    data = make_image(fmt)
    result = validate_image_upload(data=data, filename=filename, content_type=content_type)
    assert result.mime_type == mime
    assert result.width == 64 and result.height == 48
    assert result.size_bytes == len(data)


def test_no_compression_bytes_are_verbatim():
    data = make_image("PNG")
    result = validate_image_upload(data=data, filename="a.png", content_type="image/png")
    assert result.data == data, "uploads must never be recompressed"


def test_filename_is_sanitized():
    result = validate_image_upload(
        data=make_image("PNG"),
        filename="../../etc/pass wd;rm -rf.png",
        content_type="image/png",
    )
    assert "/" not in result.base_name
    assert ".." not in result.base_name
    assert " " not in result.base_name
    assert ";" not in result.base_name


def test_storage_key_is_unique_and_user_isolated():
    img = validate_image_upload(
        data=make_image("PNG"), filename="a.png", content_type="image/png"
    )
    k1 = img.storage_key(user_id=7)
    k2 = img.storage_key(user_id=7)
    assert k1 != k2, "keys must be collision-proof"
    assert k1.startswith("users/7/assets/")
    assert k1.endswith(".png")


def test_checksum_is_stable():
    data = make_image("PNG")
    a = validate_image_upload(data=data, filename="a.png", content_type="image/png")
    b = validate_image_upload(data=data, filename="b.png", content_type="image/png")
    assert a.checksum == b.checksum and len(a.checksum) == 64


# --------------------------------------------------------------------------
# Rejections
# --------------------------------------------------------------------------
def test_rejects_empty_file():
    with pytest.raises(UploadValidationError) as e:
        validate_image_upload(data=b"", filename="a.png", content_type="image/png")
    assert e.value.status_code == 400


def test_rejects_oversized_file():
    with pytest.raises(UploadValidationError) as e:
        validate_image_upload(
            data=b"x" * 11, filename="a.png", content_type="image/png", max_bytes=10
        )
    assert e.value.status_code == 413


def test_rejects_disallowed_extension():
    with pytest.raises(UploadValidationError) as e:
        validate_image_upload(data=make_image("PNG"), filename="a.gif", content_type="image/gif")
    assert e.value.status_code == 415


def test_rejects_svg_xss_vector():
    svg = b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>"
    with pytest.raises(UploadValidationError):
        validate_image_upload(data=svg, filename="a.svg", content_type="image/svg+xml")


def test_rejects_extension_mime_mismatch():
    with pytest.raises(UploadValidationError) as e:
        validate_image_upload(data=make_image("PNG"), filename="a.png", content_type="image/jpeg")
    assert e.value.status_code == 400


def test_rejects_content_spoofing():
    """A real JPEG renamed and declared as PNG must be rejected by magic-byte sniffing."""
    with pytest.raises(UploadValidationError) as e:
        validate_image_upload(data=make_image("JPEG"), filename="a.png", content_type="image/png")
    assert "declared" in e.value.message


def test_rejects_executable_disguised_as_png():
    with pytest.raises(UploadValidationError):
        validate_image_upload(
            data=b"MZ\x90\x00" + b"\x00" * 512, filename="evil.png", content_type="image/png"
        )


def test_rejects_truncated_image():
    data = make_image("PNG")[:40]
    with pytest.raises(UploadValidationError):
        validate_image_upload(data=data, filename="a.png", content_type="image/png")


def test_rejects_missing_content_type():
    with pytest.raises(UploadValidationError) as e:
        validate_image_upload(data=make_image("PNG"), filename="a.png", content_type=None)
    assert e.value.status_code == 415

"""Image upload validation helpers.

Enforces the Hackroot Studio upload contract:
  * allowed types: JPG / JPEG / PNG / WEBP
  * max size 20 MB per file
  * max 20 images per project
  * MIME validation (declared header) + extension validation + magic-byte sniffing
  * filename sanitization + collision-proof unique names
  * NO automatic compression — bytes are stored verbatim
"""
from __future__ import annotations

import hashlib
import os
import uuid
from dataclasses import dataclass
from io import BytesIO

from app.utils.files import safe_filename

MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_IMAGES_PER_PROJECT = 20

# canonical mime -> allowed extensions
ALLOWED_IMAGE_TYPES: dict[str, set[str]] = {
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
    "image/webp": {".webp"},
}
ALLOWED_IMAGE_EXTENSIONS: set[str] = {e for exts in ALLOWED_IMAGE_TYPES.values() for e in exts}

# Pillow format name -> canonical mime
_PIL_FORMAT_TO_MIME = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


class UploadValidationError(ValueError):
    """Raised when an uploaded file violates the upload contract."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class ValidatedImage:
    """Result of validating an uploaded image. Bytes are unmodified."""

    data: bytes
    mime_type: str
    extension: str
    base_name: str
    original_filename: str
    width: int
    height: int
    checksum: str

    @property
    def size_bytes(self) -> int:
        return len(self.data)

    def storage_key(self, *, user_id: int, prefix: str = "assets") -> str:
        """User-isolated, collision-proof storage key."""
        return f"users/{user_id}/{prefix}/{uuid.uuid4().hex}_{self.base_name}{self.extension}"


def _sniff(data: bytes) -> tuple[str, int, int]:
    """Return (mime, width, height) from real file content, not the client's claim."""
    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError as e:  # pragma: no cover - Pillow is a hard dependency
        raise UploadValidationError("Image validation unavailable: Pillow not installed", 500) from e

    try:
        with Image.open(BytesIO(data)) as im:
            fmt = (im.format or "").upper()
            width, height = im.size
            im.verify()
    except UnidentifiedImageError as e:
        raise UploadValidationError("File is not a valid image", 400) from e
    except UploadValidationError:
        raise
    except Exception as e:  # corrupt / truncated payloads
        raise UploadValidationError(f"Corrupt or unreadable image: {e}", 400) from e

    mime = _PIL_FORMAT_TO_MIME.get(fmt)
    if mime is None:
        raise UploadValidationError(
            f"Unsupported image format '{fmt or 'unknown'}'. Allowed: JPG, JPEG, PNG, WEBP", 415
        )
    return mime, width, height


def validate_image_upload(
    *,
    data: bytes,
    filename: str | None,
    content_type: str | None,
    max_bytes: int = MAX_IMAGE_BYTES,
) -> ValidatedImage:
    """Validate an uploaded image end to end. Never mutates or recompresses `data`."""
    if not data:
        raise UploadValidationError("Uploaded file is empty", 400)

    if len(data) > max_bytes:
        limit_mb = max_bytes / 1024 / 1024
        raise UploadValidationError(
            f"File is {len(data) / 1024 / 1024:.1f} MB — exceeds the {limit_mb:.0f} MB limit", 413
        )

    original = (filename or "upload").strip()
    stem, ext = os.path.splitext(original)
    ext = ext.lower()

    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise UploadValidationError(
            f"Unsupported file extension '{ext or '(none)'}'. Allowed: .jpg, .jpeg, .png, .webp", 415
        )

    declared = (content_type or "").split(";")[0].strip().lower()
    if declared == "image/jpg":  # common but non-standard alias
        declared = "image/jpeg"
    if declared not in ALLOWED_IMAGE_TYPES:
        raise UploadValidationError(
            f"Unsupported MIME type '{declared or '(none)'}'. Allowed: image/jpeg, image/png, image/webp",
            415,
        )
    if ext not in ALLOWED_IMAGE_TYPES[declared]:
        raise UploadValidationError(
            f"Extension '{ext}' does not match declared MIME type '{declared}'", 400
        )

    sniffed, width, height = _sniff(data)
    if sniffed != declared:
        raise UploadValidationError(
            f"File content is '{sniffed}' but was declared as '{declared}'", 400
        )

    return ValidatedImage(
        data=data,
        mime_type=sniffed,
        extension=ext,
        base_name=safe_filename(stem or "image"),
        original_filename=original[:255],
        width=width,
        height=height,
        checksum=hashlib.sha256(data).hexdigest(),
    )

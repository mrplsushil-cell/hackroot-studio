"""Password hashing & JWT helpers."""
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
from jose import JWTError, jwt

from app.config import settings

# bcrypt only consumes the first 72 bytes of input and modern releases raise
# instead of truncating silently, so we normalize here.
_BCRYPT_MAX_BYTES = 72


def _to_bcrypt_bytes(password: str) -> bytes:
    raw = password.encode("utf-8")
    if len(raw) <= _BCRYPT_MAX_BYTES:
        return raw
    # Trim on a UTF-8 character boundary.
    return raw[:_BCRYPT_MAX_BYTES].decode("utf-8", errors="ignore").encode("utf-8")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_to_bcrypt_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_to_bcrypt_bytes(plain), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str | int, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_expires_minutes)
    )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None

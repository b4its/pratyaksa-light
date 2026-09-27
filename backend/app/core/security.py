"""Password hashing & JWT helpers (bcrypt + python-jose).

The Rust backend used ``bcrypt`` + ``jsonwebtoken``.  We use the same bcrypt
scheme so that existing seeded hashes (``$2y$..``) verify unchanged.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import AppConfig
from app.core.errors import InternalError, UnauthorizedError

ALGORITHM = "HS256"
BCRYPT_ROUNDS = 12  # matches Rust ``bcrypt::DEFAULT_COST``


def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    ).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


@dataclass
class Claims:
    sub: str
    email: str
    role: str
    exp: int
    iat: int


def create_token(user_id: str, email: str, role: str, config: AppConfig) -> str:
    now = int(time.time())
    exp = now + (config.jwt_expiry_hours * 3600)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "iat": now,
        "exp": exp,
    }
    try:
        return jwt.encode(payload, config.jwt_secret, algorithm=ALGORITHM)
    except Exception as exc:  # pragma: no cover
        raise InternalError(f"Token generation failed: {exc}") from exc


def decode_token(token: str, config: AppConfig) -> Claims:
    try:
        data: dict[str, Any] = jwt.decode(token, config.jwt_secret, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise UnauthorizedError("Token tidak valid atau sudah kadaluarsa") from exc
    return Claims(
        sub=str(data.get("sub", "")),
        email=str(data.get("email", "")),
        role=str(data.get("role", "")),
        exp=int(data.get("exp", 0)),
        iat=int(data.get("iat", 0)),
    )


def new_uuid() -> str:
    return str(uuid.uuid4())

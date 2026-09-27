"""Authentication dependency: extract & validate Bearer JWT.

Mirrors the Rust ``AuthMiddleware`` — protected routes require a valid
``Authorization: Bearer <token>`` header.
"""

from __future__ import annotations

from fastapi import Depends, Request

from app.core.config import AppConfig, get_config
from app.core.errors import ServiceUnavailableError, UnauthorizedError
from app.core.security import Claims, decode_token


def _extract_bearer(request: Request) -> str:
    header = request.headers.get("Authorization")
    if not header or not header.startswith("Bearer "):
        raise UnauthorizedError("Token tidak ditemukan")
    return header[len("Bearer ") :].strip()


async def get_current_claims(
    request: Request,
    config: AppConfig = Depends(get_config),
) -> Claims:
    token = _extract_bearer(request)
    return decode_token(token, config)


# Convenience alias used by protected routers.
require_auth = get_current_claims


def get_postgres(request: Request):
    """Return the PostgreSQL pool or raise a clean 503 if unavailable."""
    pg = getattr(request.app.state, "pg", None)
    if pg is None:
        raise ServiceUnavailableError(
            "PostgreSQL tidak tersedia. Set DATABASE_URL dan pastikan database berjalan."
        )
    return pg


def get_mongo(request: Request):
    """Return the MongoDB client or raise a clean 503 if unavailable."""
    mongo = getattr(request.app.state, "mongo", None)
    if mongo is None:
        raise ServiceUnavailableError(
            "MongoDB tidak tersedia. Set MONGODB_URL dan pastikan MongoDB berjalan."
        )
    return mongo

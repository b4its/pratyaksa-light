"""Auth routes: register, login, me."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, status

from app.core.config import AppConfig, get_config
from app.core.deps import require_auth
from app.core.errors import ConflictError, NotFoundError, UnauthorizedError
from app.core.security import Claims, create_token, hash_password, new_uuid, verify_password
from app.db.postgres import PostgresDb
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserPublic

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_db(request: Request) -> PostgresDb:
    return request.app.state.pg


def _user_public(row) -> UserPublic:
    return UserPublic(
        id=str(row["id"]),
        name=row["name"],
        email=row["email"],
        role=row["role"],
        created_at=row["created_at"],
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    db: PostgresDb = Depends(_get_db),
    config: AppConfig = Depends(get_config),
) -> dict:
    existing = await db.fetchval("SELECT COUNT(*) FROM users WHERE email = $1", body.email)
    if existing and existing > 0:
        raise ConflictError("Email sudah terdaftar")

    password_hash = hash_password(body.password)
    row = await db.fetchrow(
        """
        INSERT INTO users (id, name, email, password_hash, role, created_at, updated_at)
        VALUES ($1, $2, $3, $4, 'user', NOW(), NOW())
        RETURNING *
        """,
        new_uuid(),
        body.name,
        body.email,
        password_hash,
    )
    token = create_token(str(row["id"]), row["email"], row["role"], config)
    return {
        "status": "success",
        "data": AuthResponse(token=token, user=_user_public(row)).model_dump(mode="json"),
    }


@router.post("/login")
async def login(
    body: LoginRequest,
    db: PostgresDb = Depends(_get_db),
    config: AppConfig = Depends(get_config),
) -> dict:
    row = await db.fetchrow("SELECT * FROM users WHERE email = $1", body.email)
    if row is None or not verify_password(body.password, row["password_hash"]):
        raise UnauthorizedError("Email atau password salah")

    token = create_token(str(row["id"]), row["email"], row["role"], config)
    return {
        "status": "success",
        "data": AuthResponse(token=token, user=_user_public(row)).model_dump(mode="json"),
    }


@router.get("/me")
async def me(
    claims: Claims = Depends(require_auth),
    db: PostgresDb = Depends(_get_db),
) -> dict:
    row = await db.fetchrow("SELECT * FROM users WHERE id = $1::uuid", claims.sub)
    if row is None:
        raise NotFoundError("User tidak ditemukan")
    return {"status": "success", "data": _user_public(row).model_dump(mode="json")}


# keep timezone import used for potential future expiry formatting
_ = timezone
_ = datetime

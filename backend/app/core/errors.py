"""Application error types mirroring the Rust ``AppError``."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(HTTPException):
    """Base application error. Response shape matches the Rust backend:

    ``{"status": "error", "message": "..."}``
    """

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(status_code=status_code or self.status_code, detail=message)
        self.message = message

    def to_response(self) -> JSONResponse:
        detail = self.message
        return JSONResponse(
            status_code=self.status_code,
            content={"status": "error", "message": detail},
        )


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED


class BadRequestError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST


class ValidationError(BadRequestError):
    pass


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT


class DatabaseError(AppError):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


class InternalError(AppError):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


class BadGatewayError(AppError):
    status_code = status.HTTP_502_BAD_GATEWAY


class ServiceUnavailableError(AppError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return exc.to_response()


async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    """Wrap framework HTTPExceptions in the app error envelope."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "message": str(exc.detail)},
    )


async def generic_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"status": "error", "message": f"Internal server error: {exc}"},
    )


async def integrity_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Map asyncpg integrity violations to clean 4xx responses.

    Without this, a unique/foreign-key violation surfaces as a 500 with the raw
    driver message (leaking table/constraint names). We translate the common
    cases into the standard app error envelope.
    """
    # Imported lazily so the module stays importable even if asyncpg is absent.
    try:
        from asyncpg.exceptions import (
            ForeignKeyViolationError,
            UniqueViolationError,
        )
    except Exception:  # pragma: no cover - asyncpg always present in prod
        UniqueViolationError = ()  # type: ignore[assignment]
        ForeignKeyViolationError = ()  # type: ignore[assignment]

    if isinstance(exc, UniqueViolationError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"status": "error", "message": "Data sudah ada (duplikat)"},
        )
    if isinstance(exc, ForeignKeyViolationError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status": "error",
                "message": "Referensi tidak valid (data terkait tidak ditemukan atau masih dipakai)",
            },
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"status": "error", "message": f"Internal server error: {exc}"},
    )


_FIELD_LABELS = {
    "name": "Nama",
    "email": "Email",
    "password": "Kata sandi",
    "confirm_password": "Konfirmasi kata sandi",
    "code": "Kode unit",
    "nama": "Nama jenis",
    "deskripsi": "Deskripsi",
    "jenis_alat_berat_id": "Jenis alat berat",
    "status": "Status",
    "health": "Health",
    "maintenance": "Jadwal maintenance",
    "savings": "Savings",
    "lat": "Latitude",
    "lng": "Longitude",
    "unit_id": "Unit",
    "severity": "Severity",
    "asset_code": "Kode unit",
    "status_unit": "Status unit",
}


def _field_label(loc: tuple) -> str:
    if not loc:
        return "Nilai"
    key = str(loc[-1])
    return _FIELD_LABELS.get(key, key.replace("_", " ").capitalize())


def _friendly_message(err: dict, label: str) -> str:
    """Turn a single Pydantic error into an Indonesian, field-aware message."""
    etype = err.get("type", "")
    ctx = err.get("ctx") or {}
    if etype == "missing":
        return f"{label} wajib diisi."
    if etype in ("string_too_short",):
        minimum = ctx.get("min_length", err.get("min_length"))
        return f"{label} minimal {minimum} karakter."
    if etype in ("string_too_long",):
        maximum = ctx.get("max_length")
        return f"{label} maksimal {maximum} karakter."
    if etype in ("value_error",) and "email" in err.get("msg", "").lower():
        return f"{label} tidak valid."
    if etype in ("int_parsing", "int_type", "float_parsing", "float_type", "decimal_parsing"):
        return f"{label} harus berupa angka."
    if etype in ("greater_than_equal", "less_than_equal", "greater_than", "less_than"):
        return f"{label} di luar rentang yang diizinkan."
    if etype in ("enum", "literal_error"):
        allowed = ctx.get("expected")
        return f"{label} tidak valid. Pilihan: {allowed}." if allowed else f"{label} tidak valid."
    if etype in ("value_error",):
        return f"{label} tidak valid."
    # Fallback: keep the field label but avoid leaking raw English pydantic text
    # when we can't translate it.
    raw = err.get("msg", "tidak valid")
    return f"{label}: {raw}"


def _format_validation_errors(exc: RequestValidationError) -> str:
    """Render Pydantic validation errors as friendly Indonesian messages.

    The Rust backend (via ``validator``) returned HTTP 400 with the message
    ``{"status":"error","message":"..."}``; we reproduce that envelope here but
    translate Pydantic's raw English messages (e.g. ``String should have at
    least 6 characters``) into user-facing Indonesian.
    """
    parts: list[str] = []
    for err in exc.errors():
        loc = tuple(p for p in err.get("loc", ()) if p not in ("body", "query", "path"))
        parts.append(_friendly_message(err, _field_label(loc)))
    # De-duplicate while preserving order.
    seen: set[str] = set()
    unique = [p for p in parts if not (p in seen or seen.add(p))]
    return " ".join(unique) or "Permintaan tidak valid."


async def validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Map request-body/query validation failures to 400 + app envelope.

    Matches the Rust ``JsonConfig`` error handler which produced HTTP 400 with
    ``{"status":"error","message":...}`` instead of FastAPI's default 422.
    """
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"status": "error", "message": _format_validation_errors(exc)},
    )


def success(data: Any, **extra: Any) -> dict[str, Any]:
    """Build a success envelope: ``{"status": "success", "data": ...}``."""
    payload: dict[str, Any] = {"status": "success", "data": data}
    payload.update(extra)
    return payload

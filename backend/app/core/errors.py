"""Application error types mirroring the Rust ``AppError``."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request, status
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


def success(data: Any, **extra: Any) -> dict[str, Any]:
    """Build a success envelope: ``{"status": "success", "data": ...}``."""
    payload: dict[str, Any] = {"status": "success", "data": data}
    payload.update(extra)
    return payload

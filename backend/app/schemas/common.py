"""Shared generic response schemas."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    total: int
    page: int
    per_page: int
    total_pages: int


class MessageResponse(BaseModel):
    status: str = "success"
    message: str

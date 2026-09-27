"""Schemas: jenis alat berat."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Optional

from pydantic import BaseModel, Field


class JenisAlatBerat(BaseModel):
    id: str
    nama: str
    deskripsi: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CreateJenisAlatBeratRequest(BaseModel):
    nama: Annotated[str, Field(min_length=2, max_length=200)]
    deskripsi: Optional[str] = None


class UpdateJenisAlatBeratRequest(BaseModel):
    nama: Optional[Annotated[str, Field(min_length=2, max_length=200)]] = None
    deskripsi: Optional[str] = None


class ListQuery(BaseModel):
    page: Optional[int] = None
    per_page: Optional[int] = None
    search: Optional[str] = None

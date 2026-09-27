"""Schemas: unit tambang."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Optional

from pydantic import BaseModel, Field

UNIT_STATUSES = ["SEHAT", "WARNING", "CRITICAL", "RUSAK"]


class UnitTambang(BaseModel):
    id: str
    code: str
    jenis_alat_berat_id: str
    jenis_alat_berat_nama: Optional[str] = None
    status: str
    health: int
    maintenance: str
    savings: int
    img_url: Optional[str] = None
    model3d_url: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class CreateUnitTambangRequest(BaseModel):
    code: Annotated[str, Field(min_length=2, max_length=50)]
    jenis_alat_berat_id: str
    status: str
    health: Annotated[int, Field(ge=0, le=100)]
    maintenance: Annotated[str, Field(min_length=1, max_length=200)]
    savings: int
    img_url: Optional[str] = None
    model3d_url: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None


class UpdateUnitTambangRequest(BaseModel):
    code: Optional[Annotated[str, Field(min_length=2, max_length=50)]] = None
    jenis_alat_berat_id: Optional[str] = None
    status: Optional[str] = None
    health: Optional[Annotated[int, Field(ge=0, le=100)]] = None
    maintenance: Optional[Annotated[str, Field(min_length=1, max_length=200)]] = None
    savings: Optional[int] = None
    img_url: Optional[str] = None
    model3d_url: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None


class UnitListQuery(BaseModel):
    page: Optional[int] = None
    per_page: Optional[int] = None
    search: Optional[str] = None
    status: Optional[str] = None
    jenis_alat_berat_id: Optional[str] = None

"""Schemas: analisa kerusakan (MongoDB) + dashboard stats."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SensorData(BaseModel):
    suhu_mesin: float
    tekanan_oli: float
    rpm: float
    fuel_level: float
    vibration: float
    jam_operasi: float
    timestamp: datetime


class AnalisaKerusakan(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    unit_tambang_id: str
    unit_code: str
    tipe_kerusakan: str
    deskripsi: str
    severity: str
    sensor_data: SensorData
    rekomendasi: str
    status_analisa: str
    dilaporkan_oleh: str
    created_at: datetime
    updated_at: datetime

    model_config = {"populate_by_name": True}


class CreateSensorDataRequest(BaseModel):
    suhu_mesin: float
    tekanan_oli: float
    rpm: float
    fuel_level: float
    vibration: float
    jam_operasi: float


class CreateAnalisaRequest(BaseModel):
    unit_tambang_id: str
    unit_code: str
    tipe_kerusakan: str = Field(min_length=2, max_length=200)
    deskripsi: str = Field(min_length=5)
    severity: str
    sensor_data: CreateSensorDataRequest
    rekomendasi: str
    dilaporkan_oleh: str


class UpdateAnalisaRequest(BaseModel):
    status_analisa: Optional[str] = None
    rekomendasi: Optional[str] = None
    deskripsi: Optional[str] = None


class AnalisaListQuery(BaseModel):
    page: Optional[int] = None
    per_page: Optional[int] = None
    unit_tambang_id: Optional[str] = None
    severity: Optional[str] = None
    status_analisa: Optional[str] = None


# ---- Dashboard ----
class StatusCount(BaseModel):
    label: str
    jumlah: int


class MonthStatusDetail(BaseModel):
    val: int
    units: list[str]


class MonthlyFleetData(BaseModel):
    month: str
    sehat: MonthStatusDetail
    warning: MonthStatusDetail
    critical: MonthStatusDetail


class MapLocation(BaseModel):
    id: int
    unit: str
    unit_type: str
    lat: float
    lng: float
    status: str
    level: str
    color_hex: str
    fuel: str
    operator: str
    speed: str
    temp: str
    last_update: str


class DashboardStats(BaseModel):
    total_units: int
    active_units: int
    critical_units: int
    total_savings: int
    status_distribution: list[StatusCount]
    monthly_fleet_data: list[MonthlyFleetData]
    map_locations: list[MapLocation]

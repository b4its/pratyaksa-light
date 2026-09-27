"""Schemas: telemetry (33-column sensor standard)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SensorTelemetry(BaseModel):
    id: str
    ts: datetime
    unit_id: str
    component_type: str
    operator_id: Optional[str] = None
    payload_tonnage: Optional[float] = None
    hour_meter_actual: Optional[float] = None
    design_life_hm: Optional[float] = None
    component_age_hm: Optional[float] = None
    is_remanufactured: bool = False
    ambient_temp_c: Optional[float] = None
    idle_time_ratio: Optional[float] = None
    eng_coolant_temp_c: Optional[float] = None
    eng_oil_press_psi: Optional[float] = None
    eng_rpm: Optional[float] = None
    eng_load_pct: Optional[float] = None
    hyd_pump_press_psi: Optional[float] = None
    hyd_oil_temp_c: Optional[float] = None
    trans_oil_temp_c: Optional[float] = None
    torque_converter_temp_c: Optional[float] = None
    final_drive_temp_c: Optional[float] = None
    brake_cooling_temp_c: Optional[float] = None
    battery_voltage: Optional[float] = None
    fault_code_severity: int = 0
    lab_fe_ppm: Optional[float] = None
    lab_cu_ppm: Optional[float] = None
    lab_al_ppm: Optional[float] = None
    lab_si_ppm: Optional[float] = None
    lab_viscosity_100c: Optional[float] = None
    lab_water_content_pct: Optional[float] = None
    lab_soot_pct: Optional[float] = None
    delta_eng_temp: Optional[float] = None
    status_label: Optional[str] = None
    rul_hours: Optional[float] = None
    created_at: datetime


class CreateTelemetryRequest(BaseModel):
    unit_id: str
    component_type: Optional[str] = None
    operator_id: Optional[str] = None
    payload_tonnage: Optional[float] = None
    hour_meter_actual: Optional[float] = None
    design_life_hm: Optional[float] = None
    component_age_hm: Optional[float] = None
    is_remanufactured: Optional[bool] = None
    ambient_temp_c: Optional[float] = None
    idle_time_ratio: Optional[float] = None
    eng_coolant_temp_c: Optional[float] = None
    eng_oil_press_psi: Optional[float] = None
    eng_rpm: Optional[float] = None
    eng_load_pct: Optional[float] = None
    hyd_pump_press_psi: Optional[float] = None
    hyd_oil_temp_c: Optional[float] = None
    trans_oil_temp_c: Optional[float] = None
    torque_converter_temp_c: Optional[float] = None
    final_drive_temp_c: Optional[float] = None
    brake_cooling_temp_c: Optional[float] = None
    battery_voltage: Optional[float] = None
    fault_code_severity: Optional[int] = None
    lab_fe_ppm: Optional[float] = None
    lab_cu_ppm: Optional[float] = None
    lab_al_ppm: Optional[float] = None
    lab_si_ppm: Optional[float] = None
    lab_viscosity_100c: Optional[float] = None
    lab_water_content_pct: Optional[float] = None
    lab_soot_pct: Optional[float] = None


class TelemetryQuery(BaseModel):
    limit: Optional[int] = None

"""Schemas: PRATYAKSA ML API contract (proxy/simulator)."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    redis: str = ""
    postgres: str = ""
    experts_loaded: list[str] = Field(default_factory=list)
    model_version: str = ""


class FleetAsset(BaseModel):
    asset_id: str
    equipment_type: str
    risk_level: str
    lstm_rul_hours: float
    rul_uncertainty: float
    model_agreement: bool
    drift_detected: bool
    processed_at: float


class FleetResponse(BaseModel):
    fleet: list[FleetAsset]
    total: int = 0


class DigitalTwin(BaseModel):
    brake_twin_rul: float
    bearing_twin_rul: float
    hydraulic_twin_rul: float


class DriftStatus(BaseModel):
    drift_detected: bool
    drifted_features: list[str]
    max_z_score: float
    n_drifted: int


class PredictRequest(BaseModel):
    asset_id: str
    equipment_type: str
    timestamp: str
    features: list[float]


class PredictResponse(BaseModel):
    asset_id: str = ""
    risk_level: str = ""
    lstm_rul_hours: float = 0.0
    rul_uncertainty: float = 0.0
    model_agreement: bool = False


class WorkOrderResponse(BaseModel):
    work_order_id: str = ""
    component: str = ""
    risk_score: float = 0.0
    status: str = ""


class FeaturesResponse(BaseModel):
    features: list[str] = Field(default_factory=list)
    total: int = 0


class ReloadModelsResponse(BaseModel):
    status: str = ""
    message: str = ""
    model_version: str = ""
    experts_loaded: list[str] = Field(default_factory=list)


class ModeSwitchRequest(BaseModel):
    mode: Optional[str] = None
    reset: Optional[bool] = None


# 37 standard sensor feature names — order MUST match POST /predict features[].
FEATURE_NAMES: list[str] = [
    "payload_tonnage_t",
    "hour_meter_h",
    "design_life_h",
    "component_age_h",
    "ambient_temp_c",
    "wind_speed_mps",
    "humidity_pct",
    "coolant_temp_c",
    "engine_oil_pressure_bar",
    "engine_rpm",
    "engine_load_pct",
    "hydraulic_temp_c",
    "hydraulic_pressure_bar",
    "trans_oil_temp_c",
    "torque_conv_temp_c",
    "final_drive_temp_c",
    "brake_temp_c",
    "battery_voltage_v",
    "alternator_voltage_v",
    "fault_code_count",
    "fe_ppm",
    "cu_ppm",
    "al_ppm",
    "si_ppm",
    "oil_viscosity_cst",
    "water_content_pct",
    "soot_pct",
    "delta_eng_temp_c",
    "boost_pressure_kpa",
    "exhaust_temp_c",
    "transmission_gear",
    "vibration_x_g",
    "vibration_y_g",
    "vibration_z_g",
    "fuel_consumption_lph",
    "oil_particle_count_iso",
    "acoustic_emission_db",
]

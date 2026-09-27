"""Schemas: live (predictions, fleet snapshots, work orders) from MongoDB."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class LiveDigitalTwin(BaseModel):
    brake_twin_rul: float = 0.0
    bearing_twin_rul: float = 0.0
    hydraulic_twin_rul: float = 0.0


class LiveDriftStatus(BaseModel):
    drift_detected: bool = False
    drifted_features: list[str] = Field(default_factory=list)
    max_z_score: float = 0.0
    n_drifted: int = 0


class LivePrediction(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    asset_id: str
    equipment_type: str
    timestamp: str
    xgb_anomaly_class: int
    xgb_anomaly_label: str
    lstm_rul_hours: float
    rul_uncertainty: float
    risk_level: str
    risk_class: int
    model_agreement: bool
    RUL_hydraulic_system: float = 0.0
    RUL_hydraulic_pump: float = 0.0
    RUL_pump_seal_main: float = 0.0
    RUL_brake_system: float = 0.0
    RUL_brake_caliper: float = 0.0
    RUL_brake_pad_rear: float = 0.0
    RUL_steering_system: float = 0.0
    digital_twin: LiveDigitalTwin
    drift_status: LiveDriftStatus
    processed_at: float
    latency_ms: float
    stored_at: datetime

    model_config = {"populate_by_name": True}


class LiveFleetSnapshot(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    asset_id: str
    equipment_type: str
    risk_level: str
    lstm_rul_hours: float
    rul_uncertainty: float
    model_agreement: bool
    drift_detected: bool
    processed_at: float
    stored_at: datetime

    model_config = {"populate_by_name": True}


class LiveSensorReading(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    asset_id: str
    equipment_type: str
    timestamp: str
    features: list[float]
    stored_at: datetime

    model_config = {"populate_by_name": True}


class LiveWorkOrder(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    work_order_id: str
    asset_id: str
    component: str
    risk_score: float
    status: str
    created_at: str
    stored_at: datetime

    model_config = {"populate_by_name": True}


class LiveDriftLog(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    asset_id: str
    equipment_type: str
    drifted_features: list[str]
    max_z_score: float
    n_drifted: int
    drift_detected: bool
    logged_at: str
    stored_at: datetime

    model_config = {"populate_by_name": True}

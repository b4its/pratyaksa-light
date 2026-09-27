"""Simulator: deterministic fallback data generation.

Faithfully mirrors ``backend_rust/src/pratyaksa/mod.rs::simulator``.  The
pseudo-random helpers (``frand``) match the Rust implementation so results stay
stable/comparable across stacks.
"""

from __future__ import annotations

import math
import time
from typing import Any

from app.schemas.pratyaksa import (
    FEATURE_NAMES,
    FleetAsset,
    FleetResponse,
    HealthResponse,
    PredictRequest,
    PredictResponse,
    ReloadModelsResponse,
    WorkOrderResponse,
)


def frand(seed: float) -> float:
    x = math.sin(seed * 12.9898 + 78.233) * 43758.5453
    return x - math.floor(x)


def time_bucket(interval_secs: int) -> float:
    now = int(time.time())
    return float(now // interval_secs)


def seed_from_string(s: str) -> float:
    return float(sum(ord(b) for b in s) + len(s))


def r1(x: float) -> float:
    return round(x * 10.0) / 10.0


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


FLEET_DEFS: list[tuple[str, str]] = [
    ("WA600-001", "wheel_loader"),
    ("HD785-001", "haul_truck"),
    ("HD785-002", "haul_truck"),
    ("D155-001", "bulldozer"),
    ("PC2000-001", "excavator"),
    ("DT-001", "haul_truck"),
]


def generate_health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        redis="simulasi",
        postgres="simulasi",
        experts_loaded=["bulldozer", "haul_truck", "excavator", "wheel_loader"],
        model_version="2.0.0-simulasi",
    )


def generate_fleet() -> list[FleetAsset]:
    now = time.time()
    assets: list[FleetAsset] = []
    for asset_id, eq_type in FLEET_DEFS:
        seed = seed_from_string(asset_id)
        t = time_bucket(300)
        base_degr = frand(seed * 1.7 + 13.0)
        time_jitter = frand(seed + t * 0.05) * 0.15
        degr = _clamp(base_degr + time_jitter, 0.0, 1.0)

        if degr < 0.3:
            risk_level = "NORMAL"
        elif degr < 0.55:
            risk_level = "WARNING"
        else:
            risk_level = "CRITICAL"

        rul_max = 2000.0
        lstm_rul = r1(_clamp((1.0 - degr) * rul_max * (0.6 + frand(seed + 60.0) * 0.4), 0.0, rul_max))
        uncertainty = r1(lstm_rul * (0.05 + degr * 0.15) + 3.0)
        drift = frand(seed + t + 90.0) > 0.6

        assets.append(
            FleetAsset(
                asset_id=asset_id,
                equipment_type=eq_type,
                risk_level=risk_level,
                lstm_rul_hours=lstm_rul,
                rul_uncertainty=uncertainty,
                model_agreement=frand(seed + 50.0) > 0.2,
                drift_detected=drift,
                processed_at=now,
            )
        )
    return assets


def _equipment_type_for(asset_id: str) -> str:
    if asset_id.startswith("WA"):
        return "wheel_loader"
    if asset_id.startswith("HD"):
        return "haul_truck"
    if asset_id.startswith("D1"):
        return "bulldozer"
    if asset_id.startswith("PC"):
        return "excavator"
    return "haul_truck"


def generate_result(asset_id: str) -> dict[str, Any]:
    eq_type = _equipment_type_for(asset_id)
    seed = seed_from_string(asset_id)
    t = time_bucket(300)
    base_degr = frand(seed * 1.7 + 13.0)
    time_jitter = frand(seed + t * 0.05) * 0.15
    degr = _clamp(base_degr + time_jitter, 0.0, 1.0)

    if degr < 0.5:
        xgb_class = 0
    elif degr < 0.78:
        xgb_class = 1
    else:
        xgb_class = 2

    rul_max = 2000.0
    lstm_rul = r1(_clamp((1.0 - degr) * rul_max * (0.7 + frand(seed + 60.0) * 0.5), 8.0, rul_max))
    uncertainty = r1(lstm_rul * (0.08 + degr * 0.12) + 2.0)

    if lstm_rul < 120.0:
        lstm_class = 2
    elif lstm_rul < 400.0:
        lstm_class = 1
    else:
        lstm_class = 0

    risk_class = max(xgb_class, lstm_class)
    labels = ["NORMAL", "WARNING", "CRITICAL"]
    xgb_label = labels[xgb_class]
    risk_lbl = labels[risk_class]
    model_agreement = xgb_class == lstm_class

    def comp(nominal: float, idx: float) -> float:
        return r1(_clamp((1.0 - degr) * nominal * (0.6 + frand(seed + 70.0 + idx) * 0.6), 10.0, nominal))

    drift_detected = frand(seed + t + 90.0) > 0.75
    max_z_score = r1(0.6 + frand(seed + t + 91.0) * 2.4)
    now = time.time()

    feat_pool = [
        "engine_oil_temp_c",
        "vibration_z_g",
        "coolant_temp_c",
        "acoustic_emission_db",
        "oil_particle_count_iso",
    ]
    if drift_detected:
        n = 1 + int(frand(seed + 92.0) * 2.0)
        drifted = feat_pool[: min(n, len(feat_pool))]
    else:
        drifted = []

    return {
        "asset_id": asset_id,
        "equipment_type": eq_type,
        "timestamp": _rfc3339_now(),
        "xgb_anomaly_class": xgb_class,
        "xgb_anomaly_label": xgb_label,
        "lstm_rul_hours": lstm_rul,
        "rul_uncertainty": uncertainty,
        "risk_level": risk_lbl,
        "risk_class": risk_class,
        "model_agreement": model_agreement,
        "RUL_hydraulic_system": comp(900.0, 1.0),
        "RUL_hydraulic_pump": comp(760.0, 2.0),
        "RUL_pump_seal_main": comp(560.0, 3.0),
        "RUL_brake_system": comp(820.0, 4.0),
        "RUL_brake_caliper": comp(640.0, 5.0),
        "RUL_brake_pad_rear": comp(360.0, 6.0),
        "RUL_steering_system": comp(880.0, 7.0),
        "digital_twin": {
            "brake_twin_rul": comp(700.0, 8.0),
            "bearing_twin_rul": comp(900.0, 9.0),
            "hydraulic_twin_rul": comp(820.0, 10.0),
        },
        "drift_status": {
            "drift_detected": drift_detected,
            "drifted_features": drifted,
            "max_z_score": max_z_score,
            "n_drifted": (1 + int(frand(seed + 93.0) * 2.0)) if drift_detected else 0,
        },
        "processed_at": now,
        "latency_ms": r1(28.0 + frand(seed + t + 92.0) * 40.0),
    }


def _rfc3339_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def generate_workorder(component: str, risk_score: float) -> WorkOrderResponse:
    allowed = ["brake", "hydraulic", "engine", "transmission"]
    comp = component if component in allowed else "brake"
    risk = _clamp(risk_score, 0.0, 1.0)
    return WorkOrderResponse(
        work_order_id=f"WO-SIM-{int(frand(seed_from_string(comp) + risk) * 999999.0):06d}",
        component=comp,
        risk_score=risk,
        status="CREATED",
    )


def generate_predict(req: PredictRequest) -> PredictResponse:
    seed = seed_from_string(req.asset_id)
    t = time_bucket(5)
    degr = frand(seed + t * 0.1)
    rul_max = 2000.0
    lstm_rul = r1(_clamp((1.0 - degr) * rul_max * (0.7 + frand(seed + 60.0) * 0.5), 8.0, rul_max))
    if degr < 0.5:
        risk_level = "NORMAL"
    elif degr < 0.78:
        risk_level = "WARNING"
    else:
        risk_level = "CRITICAL"
    return PredictResponse(
        asset_id=req.asset_id,
        risk_level=risk_level,
        lstm_rul_hours=lstm_rul,
        rul_uncertainty=r1(lstm_rul * (0.08 + degr * 0.12) + 2.0),
        model_agreement=frand(seed + 50.0) > 0.25,
    )


def generate_features() -> dict[str, Any]:
    return {"features": list(FEATURE_NAMES), "total": len(FEATURE_NAMES)}


def generate_reload_models() -> ReloadModelsResponse:
    return ReloadModelsResponse(
        status="ok",
        message="Model reloaded successfully (simulated)",
        model_version="2.0.0-simulasi",
        experts_loaded=["bulldozer", "haul_truck", "excavator", "wheel_loader"],
    )


def generate_explain() -> dict[str, Any]:
    return {
        "prediction_id": "sim-000000",
        "shap_values": [
            {"feature": "payload_tonnage_t", "value": 0.42},
            {"feature": "hour_meter_h", "value": 0.35},
            {"feature": "engine_oil_temp_c", "value": -0.28},
            {"feature": "vibration_z_g", "value": 0.22},
            {"feature": "coolant_temp_c", "value": -0.18},
            {"feature": "oil_viscosity_cst", "value": 0.15},
            {"feature": "acoustic_emission_db", "value": 0.12},
            {"feature": "brake_temp_c", "value": -0.10},
        ],
        "base_value": 0.0,
        "prediction_class": 1,
        "prediction_label": "WARNING",
    }

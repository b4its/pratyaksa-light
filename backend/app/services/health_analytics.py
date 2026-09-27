"""Health analytics derivation.

Ports ``backend_rust/src/routes/health_analytics.rs``.  In SIMULASI mode there
are no physical IoT sensors, so telemetry values are derived deterministically
from ``health`` + ``status`` with time-based variation to look realtime.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

OPERATORS = [
    "OP-Budi S.",
    "OP-Joko P.",
    "OP-Agus T.",
    "OP-Rian M.",
    "OP-Deni R.",
    "OP-Siti N.",
    "OP-Eko W.",
]

COMPONENTS = ["Engine", "Hidrolik", "Transmisi", "Rem", "Bearing", "Kelistrikan"]
RISK_LABELS = ["NORMAL", "WARNING", "CRITICAL"]


def frand(seed: float) -> float:
    x = math.sin(seed * 12.9898 + 78.233) * 43758.5453
    return x - math.floor(x)


def code_seed(code: str) -> float:
    return float(sum(ord(b) for b in code) + len(code))


def time_bucket() -> float:
    return float(int(datetime.now(timezone.utc).timestamp()) // 5)


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _round(v: float) -> int:
    return int(round(v))


def risk_level(score: float) -> str:
    if score < 30.0:
        return "LOW"
    if score < 55.0:
        return "MEDIUM"
    if score < 80.0:
        return "HIGH"
    return "CRITICAL"


def unit_kind(jenis: Optional[str]) -> str:
    j = (jenis or "").lower()
    if "excavator" in j or "zaxis" in j:
        return "Excavator"
    if "dump" in j or "truck" in j or "haul" in j:
        return "Dump Truck"
    if "dozer" in j:
        return "Bulldozer"
    if "loader" in j:
        return "Wheel Loader"
    return "Heavy Equipment"


def equipment_type_slug(jenis: Optional[str]) -> str:
    return {
        "Excavator": "excavator",
        "Dump Truck": "haul_truck",
        "Bulldozer": "dozer",
        "Wheel Loader": "wheel_loader",
    }.get(unit_kind(jenis), "heavy_equipment")


def classify_status(
    eng_coolant: float,
    eng_oil_press: float,
    hyd_oil_temp: float,
    brake_temp: float,
    battery: float,
    fe_ppm: float,
    water_pct: float,
    soot_pct: float,
    fault_sev: int,
) -> str:
    if (
        eng_coolant > 110.0
        or eng_oil_press < 25.0
        or hyd_oil_temp > 100.0
        or brake_temp > 95.0
        or battery < 23.0
        or fe_ppm > 100.0
        or water_pct > 0.5
        or fault_sev >= 3
    ):
        return "CRITICAL"
    if (
        eng_coolant > 100.0
        or eng_oil_press < 35.0
        or hyd_oil_temp > 90.0
        or brake_temp > 85.0
        or fe_ppm > 60.0
        or soot_pct > 3.0
        or fault_sev >= 2
    ):
        return "WARNING"
    return "NORMAL"


def derive_telemetry(unit: dict[str, Any]) -> dict[str, Any]:
    health = float(unit["health"])
    seed = code_seed(unit["code"])
    t = time_bucket()
    degr = _clamp((100.0 - health) / 100.0, 0.0, 1.0)
    jenis = unit.get("jenis_alat_berat_nama")
    kind = unit_kind(jenis)

    design_life_hm = {
        "Dump Truck": 24000.0,
        "Excavator": 20000.0,
        "Bulldozer": 18000.0,
        "Wheel Loader": 16000.0,
    }.get(kind, 20000.0)

    hour_meter_actual = _round(4000.0 + frand(seed + 11.0) * 18000.0)
    component_age_hm = _round(
        _clamp(
            design_life_hm * (0.25 + degr * 0.7) + (frand(seed + 12.0) - 0.5) * 800.0,
            200.0,
            design_life_hm * 1.05,
        )
    )
    is_remanufactured = frand(seed + 13.0) > 0.6

    operator_id = OPERATORS[(int(seed) + int(t)) % len(OPERATORS)]
    if kind == "Dump Truck":
        payload_tonnage = _round(88.0 + frand(seed + t + 20.0) * 14.0)
    elif kind == "Wheel Loader":
        payload_tonnage = round((10.0 + frand(seed + t + 20.0) * 4.0 * 10.0)) / 10.0
    else:
        payload_tonnage = 0.0

    ambient_temp_c = _round(27.0 + frand(seed + t + 21.0) * 9.0)
    idle_time_ratio = round((0.12 + frand(seed + t + 22.0) * 0.28) * 100.0) / 100.0
    eng_coolant_temp_c = _clamp(82.0 + degr * 38.0 + (frand(seed + t + 1.0) - 0.5) * 5.0, 70.0, 128.0)
    eng_oil_press_psi = _clamp(62.0 - degr * 40.0 + (frand(seed + t + 2.0) - 0.5) * 4.0, 15.0, 72.0)
    eng_rpm = _round(1300.0 + frand(seed + t + 3.0) * 650.0)
    eng_load_pct = _round(45.0 + frand(seed + t + 4.0) * 50.0)
    hyd_pump_press_psi = _round(3400.0 - degr * 700.0 + (frand(seed + t + 5.0) - 0.5) * 150.0)
    hyd_oil_temp_c = _clamp(72.0 + degr * 35.0 + (frand(seed + t + 6.0) - 0.5) * 4.0, 60.0, 115.0)
    trans_oil_temp_c = _clamp(78.0 + degr * 30.0 + (frand(seed + t + 7.0) - 0.5) * 4.0, 65.0, 118.0)
    torque_converter_temp_c = _clamp(85.0 + degr * 32.0 + (frand(seed + t + 8.0) - 0.5) * 4.0, 70.0, 125.0)
    final_drive_temp_c = _clamp(74.0 + degr * 30.0 + (frand(seed + t + 9.0) - 0.5) * 4.0, 60.0, 110.0)
    brake_cooling_temp_c = _clamp(60.0 + degr * 42.0 + (frand(seed + t + 10.0) - 0.5) * 5.0, 45.0, 110.0)
    battery_voltage = round((27.8 - degr * 5.5 + (frand(seed + t + 14.0) - 0.5) * 0.6) * 10.0) / 10.0
    fault_code_severity = int(_clamp(math.floor(degr * 4.2 + frand(seed + t + 15.0) * 0.8), 0.0, 4.0))

    lab_fe_ppm = _round(_clamp(15.0 + degr * 130.0 + (frand(seed + t + 16.0) - 0.5) * 8.0, 5.0, 220.0))
    lab_cu_ppm = _round(_clamp(3.0 + degr * 40.0 + (frand(seed + t + 17.0) - 0.5) * 3.0, 1.0, 70.0))
    lab_al_ppm = _round(_clamp(2.0 + degr * 28.0 + (frand(seed + t + 18.0) - 0.5) * 2.0, 0.0, 50.0))
    lab_si_ppm = _round(_clamp(5.0 + degr * 35.0 + (frand(seed + t + 19.0) - 0.5) * 3.0, 2.0, 60.0))
    lab_viscosity_100c = round((15.0 - degr * 3.0 + (frand(seed + 23.0) - 0.5) * 0.6) * 10.0) / 10.0
    lab_water_content_pct = round((0.03 + degr * 0.7 + (frand(seed + t + 24.0) - 0.5) * 0.04) * 100.0) / 100.0
    lab_soot_pct = round((0.4 + degr * 4.0 + (frand(seed + t + 25.0) - 0.5) * 0.2) * 10.0) / 10.0

    delta_eng_temp = round(eng_coolant_temp_c - ambient_temp_c)
    status_label = classify_status(
        eng_coolant_temp_c,
        eng_oil_press_psi,
        hyd_oil_temp_c,
        brake_cooling_temp_c,
        battery_voltage,
        lab_fe_ppm,
        lab_water_content_pct,
        lab_soot_pct,
        fault_code_severity,
    )
    base_rul = max(design_life_hm - component_age_hm, 0.0)
    severity_factor = 1.0 - (fault_code_severity * 0.12)
    rul_hours = round(base_rul * max(severity_factor, 0.2))

    return {
        "component_type": kind,
        "operator_id": operator_id,
        "payload_tonnage": payload_tonnage,
        "hour_meter_actual": hour_meter_actual,
        "design_life_hm": design_life_hm,
        "component_age_hm": component_age_hm,
        "is_remanufactured": is_remanufactured,
        "ambient_temp_c": ambient_temp_c,
        "idle_time_ratio": idle_time_ratio,
        "eng_coolant_temp_c": _round(eng_coolant_temp_c),
        "eng_oil_press_psi": _round(eng_oil_press_psi),
        "eng_rpm": eng_rpm,
        "eng_load_pct": eng_load_pct,
        "hyd_pump_press_psi": hyd_pump_press_psi,
        "hyd_oil_temp_c": _round(hyd_oil_temp_c),
        "trans_oil_temp_c": _round(trans_oil_temp_c),
        "torque_converter_temp_c": _round(torque_converter_temp_c),
        "final_drive_temp_c": _round(final_drive_temp_c),
        "brake_cooling_temp_c": _round(brake_cooling_temp_c),
        "battery_voltage": battery_voltage,
        "fault_code_severity": fault_code_severity,
        "lab_fe_ppm": lab_fe_ppm,
        "lab_cu_ppm": lab_cu_ppm,
        "lab_al_ppm": lab_al_ppm,
        "lab_si_ppm": lab_si_ppm,
        "lab_viscosity_100c": lab_viscosity_100c,
        "lab_water_content_pct": lab_water_content_pct,
        "lab_soot_pct": lab_soot_pct,
        "delta_eng_temp": delta_eng_temp,
        "status_label": status_label,
        "rul_hours": rul_hours,
    }


def derive_prediction(unit: dict[str, Any]) -> dict[str, Any]:
    health = float(unit["health"])
    seed = code_seed(unit["code"])
    t = time_bucket()
    degr = _clamp((100.0 - health) / 100.0, 0.0, 1.0)

    def r1(x: float) -> float:
        return round(x * 10.0) / 10.0

    status = unit["status"]
    if status in ("CRITICAL", "RUSAK") or degr > 0.68:
        xgb_class = 2
    elif status == "WARNING" or degr > 0.4:
        xgb_class = 1
    else:
        xgb_class = 0

    rul_max = 2000.0
    lstm_rul_hours = r1(_clamp((1.0 - degr) * rul_max * (0.7 + frand(seed + 60.0) * 0.5), 8.0, rul_max))
    rul_uncertainty = r1(lstm_rul_hours * (0.08 + degr * 0.12) + 2.0)

    if lstm_rul_hours < 120.0:
        lstm_class = 2
    elif lstm_rul_hours < 400.0:
        lstm_class = 1
    else:
        lstm_class = 0

    risk_class = max(xgb_class, lstm_class)
    model_agreement = xgb_class == lstm_class

    def comp(nominal: float, idx: float) -> float:
        return r1(_clamp((1.0 - degr) * nominal * (0.6 + frand(seed + 70.0 + idx) * 0.6), 10.0, nominal))

    max_z_score = r1(0.6 + frand(seed + t + 90.0) * 2.4)
    drift_detected = max_z_score > 2.5
    feat_pool = [
        "engine_oil_temp_c",
        "vibration_z_g",
        "coolant_temp_c",
        "acoustic_emission_db",
        "oil_particle_count_iso",
    ]
    drifted_features = feat_pool[: min(1 + int(frand(seed + 91.0) * 2.0), len(feat_pool))] if drift_detected else []
    latency_ms = r1(28.0 + frand(seed + t + 92.0) * 40.0)

    return {
        "asset_id": unit["code"],
        "equipment_type": equipment_type_slug(unit.get("jenis_alat_berat_nama")),
        "xgb_anomaly_class": xgb_class,
        "xgb_anomaly_label": RISK_LABELS[xgb_class],
        "lstm_rul_hours": lstm_rul_hours,
        "rul_uncertainty": rul_uncertainty,
        "risk_level": RISK_LABELS[risk_class],
        "risk_class": risk_class,
        "model_agreement": model_agreement,
        "lstm_hydraulic_system": comp(900.0, 1.0),
        "lstm_hydraulic_pump": comp(760.0, 2.0),
        "lstm_pump_seal": comp(560.0, 3.0),
        "lstm_brake_system": comp(820.0, 4.0),
        "lstm_brake_caliper": comp(640.0, 5.0),
        "lstm_brake_pad": comp(360.0, 6.0),
        "lstm_steering_system": comp(880.0, 7.0),
        "digital_twin": {
            "brake_twin_rul": comp(700.0, 8.0),
            "bearing_twin_rul": comp(900.0, 9.0),
            "hydraulic_twin_rul": comp(820.0, 10.0),
        },
        "drift_status": {
            "drift_detected": drift_detected,
            "drifted_features": drifted_features,
            "max_z_score": max_z_score,
            "n_drifted": len(drifted_features),
        },
        "latency_ms": latency_ms,
    }


def derive_operational(unit: dict[str, Any]) -> dict[str, Any]:
    health = float(unit["health"])
    seed = code_seed(unit["code"])
    t = time_bucket()
    degr = _clamp((100.0 - health) / 100.0, 0.0, 1.0)

    return {
        "road_grade_pct": round((4.0 + frand(seed + t + 30.0) * 8.0) * 10.0) / 10.0,
        "haul_distance_km": round((2.0 + frand(seed + t + 31.0) * 6.0) * 10.0) / 10.0,
        "cycle_time_minutes": round((18.0 + frand(seed + t + 32.0) * 14.0) * 10.0) / 10.0,
        "dust_concentration_mgm3": round((0.5 + frand(seed + t + 33.0) * 3.5) * 100.0) / 100.0,
        "humidity_pct": _round(62.0 + frand(seed + t + 34.0) * 30.0),
        "days_since_last_pm": _round(frand(seed + 35.0) * 45.0),
        "last_maintenance_hours": _round(200.0 + frand(seed + 36.0) * 900.0),
        "oil_change_flag": frand(seed + 37.0) > 0.7,
        "fuel_consumption_rate_lph": _round(35.0 + frand(seed + t + 38.0) * 45.0 + degr * 15.0),
        "boost_pressure_kpa": _round(180.0 + frand(seed + t + 39.0) * 60.0 - degr * 40.0),
        "exhaust_gas_temp_c": _round(380.0 + degr * 180.0 + (frand(seed + t + 40.0) - 0.5) * 30.0),
        "engine_oil_temp_c": _round(95.0 + degr * 30.0 + (frand(seed + t + 41.0) - 0.5) * 4.0),
        "coolant_pressure_kpa": _round(90.0 + frand(seed + t + 42.0) * 40.0 - degr * 20.0),
        "vibration_x_g": round((1.0 + degr * 5.0 + (frand(seed + t + 43.0) - 0.5) * 0.5) * 100.0) / 100.0,
        "vibration_y_g": round((1.1 + degr * 5.2 + (frand(seed + t + 44.0) - 0.5) * 0.5) * 100.0) / 100.0,
        "vibration_z_g": round((1.3 + degr * 6.0 + (frand(seed + t + 45.0) - 0.5) * 0.5) * 100.0) / 100.0,
        "oil_viscosity_cst": round((14.0 - degr * 3.0 + (frand(seed + 46.0) - 0.5) * 0.6) * 10.0) / 10.0,
        "oil_particle_count_iso": _round(13.0 + degr * 9.0 + (frand(seed + t + 47.0) - 0.5)),
        "oil_moisture_pct": round((0.03 + degr * 0.7) * 100.0) / 100.0,
        "wear_metal_fe_ppm": _round(15.0 + degr * 130.0),
        "wear_metal_cu_ppm": _round(3.0 + degr * 40.0),
    }


def derive_unit_analysis(unit: dict[str, Any]) -> dict[str, Any]:
    health = float(unit["health"])
    seed = code_seed(unit["code"])
    t = time_bucket()
    degr = _clamp((100.0 - health) / 100.0, 0.0, 1.0)

    wobble = (frand(seed + t) - 0.5) * 6.0
    risk_score = (100.0 - health) + wobble
    if unit["status"] == "RUSAK":
        risk_score += 15.0
    elif unit["status"] == "CRITICAL":
        risk_score += 8.0
    risk_score = _clamp(risk_score, 0.0, 100.0)

    suhu_mesin = _clamp(78.0 + degr * 45.0 + (frand(seed + t + 1.0) - 0.5) * 4.0, 60.0, 130.0)
    vibration = _clamp(1.5 + degr * 6.5 + (frand(seed + t + 2.0) - 0.5) * 0.6, 0.5, 10.0)
    tekanan_oli = _clamp(6.8 - degr * 3.2 + (frand(seed + t + 3.0) - 0.5) * 0.3, 1.5, 8.0)
    rpm = _round(1300.0 + frand(seed + t + 4.0) * 650.0)
    fuel_level = _round(22.0 + frand(seed + 9.0) * 73.0)
    oil_particle_iso = _round(13.0 + degr * 9.0 + (frand(seed + t + 6.0) - 0.5) * 1.0)
    acoustic_db = _clamp(42.0 + degr * 55.0 + (frand(seed + t + 7.0) - 0.5) * 5.0, 35.0, 120.0)
    jam_operasi = _round(4000.0 + frand(seed + 11.0) * 16000.0)

    component_health = []
    for i, name in enumerate(COMPONENTS):
        v = _clamp(health + (frand(seed + i * 10.0) - 0.5) * 28.0, 3.0, 100.0)
        component_health.append({"component": name, "health": _round(v)})

    weak_idx, weak_health = min(
        ((i, c["health"]) for i, c in enumerate(component_health)),
        key=lambda x: x[1],
    )

    rul_hours = _round(weak_health * 11.0 + frand(seed + 5.0) * 80.0)
    rul_confidence = _round(72.0 + frand(seed + 8.0) * 23.0)
    rul_lower = _round(rul_hours * 0.82)
    rul_upper = _round(rul_hours * 1.18)

    shap = [
        {"feature": f"Suhu {COMPONENTS[weak_idx]}", "value": _round((suhu_mesin - 80.0) * 0.9)},
        {"feature": "Vibrasi 3-axis", "value": _round(vibration * 6.0 - 12.0)},
        {"feature": "Tekanan Hidrolik", "value": _round((6.8 - tekanan_oli) * 7.0)},
        {"feature": "Partikel Oli (ISO)", "value": _round((oil_particle_iso - 14.0) * 3.0)},
        {"feature": "Emisi Akustik", "value": _round((acoustic_db - 50.0) * 0.4)},
        {"feature": "Jam Operasi", "value": _round((jam_operasi / 1000.0) - 8.0)},
    ]

    now = datetime.now(timezone.utc)
    history = []
    for h in reversed(range(24)):
        ts = now - timedelta(hours=h)
        progress = (24 - h) / 24.0
        trend = degr * progress
        hseed = seed + h
        history.append(
            {
                "time": ts.strftime("%H:00"),
                "suhu_mesin": _round(76.0 + trend * 44.0 + (frand(hseed + 1.0) - 0.5) * 3.0),
                "vibration": round((1.4 + trend * 6.0 + (frand(hseed + 2.0) - 0.5) * 0.5) * 10.0) / 10.0,
                "tekanan_oli": round((6.8 - trend * 3.0 + (frand(hseed + 3.0) - 0.5) * 0.25) * 10.0) / 10.0,
                "acoustic": _round(42.0 + trend * 52.0 + (frand(hseed + 4.0) - 0.5) * 4.0),
            }
        )

    return {
        "unit": {
            "id": unit["id"],
            "code": unit["code"],
            "jenis_alat_berat_nama": unit.get("jenis_alat_berat_nama"),
            "status": unit["status"],
            "health": unit["health"],
            "img_url": unit.get("img_url"),
            "model3d_url": unit.get("model3d_url"),
        },
        "risk_score": _round(risk_score),
        "risk_level": risk_level(risk_score),
        "sensor_readings": {
            "suhu_mesin": _round(suhu_mesin),
            "vibration": round(vibration * 10.0) / 10.0,
            "tekanan_oli": round(tekanan_oli * 10.0) / 10.0,
            "rpm": rpm,
            "fuel_level": fuel_level,
            "oil_particle_iso": oil_particle_iso,
            "acoustic_db": _round(acoustic_db),
            "jam_operasi": jam_operasi,
        },
        "component_health": component_health,
        "rul_prediction": {
            "component": COMPONENTS[weak_idx],
            "hours_remaining": rul_hours,
            "lower_bound": rul_lower,
            "upper_bound": rul_upper,
            "confidence": rul_confidence,
        },
        "shap_contributions": shap,
        "sensor_history": history,
        "telemetry": derive_telemetry(unit),
        "prediction": derive_prediction(unit),
        "operational": derive_operational(unit),
        "updated_at": now.isoformat(),
    }

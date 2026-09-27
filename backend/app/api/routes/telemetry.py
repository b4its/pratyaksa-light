"""Telemetry ingestion & history routes (PostgreSQL)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status

from app.core.deps import get_postgres, require_auth
from app.core.errors import NotFoundError
from app.db.postgres import PostgresDb
from app.schemas.telemetry import CreateTelemetryRequest

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


def _get_db(request: Request) -> PostgresDb:
    return get_postgres(request)


def _serialize(row) -> dict:
    out = dict(row)
    out["id"] = str(out["id"])
    out["unit_id"] = str(out["unit_id"])
    for key in ("ts", "created_at"):
        if out.get(key) is not None:
            out[key] = out[key].isoformat()
    return out


def classify(
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


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_auth)])
async def create(body: CreateTelemetryRequest, db: PostgresDb = Depends(_get_db)) -> dict:
    exists = await db.fetchval(
        "SELECT COUNT(*) FROM unit_tambang WHERE id = $1::uuid", body.unit_id
    )
    if not exists:
        raise NotFoundError("Unit tidak ditemukan")

    ambient = body.ambient_temp_c if body.ambient_temp_c is not None else 30.0
    eng_coolant = body.eng_coolant_temp_c if body.eng_coolant_temp_c is not None else 85.0
    eng_oil_press = body.eng_oil_press_psi if body.eng_oil_press_psi is not None else 55.0
    hyd_oil_temp = body.hyd_oil_temp_c if body.hyd_oil_temp_c is not None else 80.0
    brake_temp = body.brake_cooling_temp_c if body.brake_cooling_temp_c is not None else 65.0
    battery = body.battery_voltage if body.battery_voltage is not None else 27.5
    fe = body.lab_fe_ppm if body.lab_fe_ppm is not None else 20.0
    water = body.lab_water_content_pct if body.lab_water_content_pct is not None else 0.05
    soot = body.lab_soot_pct if body.lab_soot_pct is not None else 0.5
    fault_sev = body.fault_code_severity if body.fault_code_severity is not None else 0

    delta_eng_temp = eng_coolant - ambient
    status_label = classify(
        eng_coolant, eng_oil_press, hyd_oil_temp, brake_temp, battery, fe, water, soot, fault_sev
    )
    design = body.design_life_hm if body.design_life_hm is not None else 20000.0
    age = body.component_age_hm if body.component_age_hm is not None else 0.0
    rul_hours = round(max(design - age, 0.0) * max(1.0 - fault_sev * 0.12, 0.2))

    row = await db.fetchrow(
        """
        INSERT INTO sensor_telemetry (
            unit_id, component_type, operator_id, payload_tonnage,
            hour_meter_actual, design_life_hm, component_age_hm, is_remanufactured,
            ambient_temp_c, idle_time_ratio, eng_coolant_temp_c, eng_oil_press_psi,
            eng_rpm, eng_load_pct, hyd_pump_press_psi, hyd_oil_temp_c, trans_oil_temp_c,
            torque_converter_temp_c, final_drive_temp_c, brake_cooling_temp_c, battery_voltage,
            fault_code_severity, lab_fe_ppm, lab_cu_ppm, lab_al_ppm, lab_si_ppm,
            lab_viscosity_100c, lab_water_content_pct, lab_soot_pct,
            delta_eng_temp, status_label, rul_hours
        ) VALUES (
            $1::uuid,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,
            $22,$23,$24,$25,$26,$27,$28,$29,$30,$31,$32
        )
        RETURNING *
        """,
        body.unit_id,
        body.component_type or "Heavy Equipment",
        body.operator_id,
        body.payload_tonnage,
        body.hour_meter_actual,
        body.design_life_hm,
        body.component_age_hm,
        bool(body.is_remanufactured) if body.is_remanufactured is not None else False,
        body.ambient_temp_c,
        body.idle_time_ratio,
        body.eng_coolant_temp_c,
        body.eng_oil_press_psi,
        body.eng_rpm,
        body.eng_load_pct,
        body.hyd_pump_press_psi,
        body.hyd_oil_temp_c,
        body.trans_oil_temp_c,
        body.torque_converter_temp_c,
        body.final_drive_temp_c,
        body.brake_cooling_temp_c,
        body.battery_voltage,
        fault_sev,
        body.lab_fe_ppm,
        body.lab_cu_ppm,
        body.lab_al_ppm,
        body.lab_si_ppm,
        body.lab_viscosity_100c,
        body.lab_water_content_pct,
        body.lab_soot_pct,
        delta_eng_temp,
        status_label,
        rul_hours,
    )
    return {"status": "success", "data": _serialize(row)}


@router.get("/unit/{unit_id}", dependencies=[Depends(require_auth)])
async def list_by_unit(
    unit_id: str,
    db: PostgresDb = Depends(_get_db),
    limit: int | None = Query(None),
) -> dict:
    _limit = min(max(limit or 100, 1), 1000)
    rows = await db.fetch(
        "SELECT * FROM sensor_telemetry WHERE unit_id = $1::uuid ORDER BY ts DESC LIMIT $2",
        unit_id,
        _limit,
    )
    return {"status": "success", "data": [_serialize(r) for r in rows]}

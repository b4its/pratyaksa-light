"""Health Analytics routes: fleet overview & per-unit realtime analysis."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request

from app.core.deps import require_auth
from app.core.errors import BadRequestError, NotFoundError
from app.db.postgres import PostgresDb
from app.pratyaksa.state import (
    PratyaksaApiClient,
    PratyaksaMode,
    SharedPratyaksaState,
)
from app.services import health_analytics as ha

router = APIRouter(prefix="/analisa", tags=["analisa-health"])


def _get_db(request: Request) -> PostgresDb:
    return request.app.state.pg


def _get_state(request: Request) -> SharedPratyaksaState:
    return request.app.state.pratyaksa


def _get_client(request: Request) -> PratyaksaApiClient:
    return request.app.state.pratyaksa_client


def _uuid5_dns(name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, name))


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/overview", dependencies=[Depends(require_auth)])
async def get_overview(
    db: PostgresDb = Depends(_get_db),
    state: SharedPratyaksaState = Depends(_get_state),
) -> dict:
    current = await state.read()
    mode = current.mode
    reachable = current.api_reachable

    if mode == PratyaksaMode.LIVE and reachable:
        fleet = [a.model_dump() for a in current.fleet_data]
        total = len(fleet)
        status_count: dict[str, int] = {}
        risk_count: dict[str, int] = {}
        sum_risk = 0.0
        sum_rul = 0.0
        unit_summaries = []

        for asset in fleet:
            rl = asset["risk_level"]
            status_count[rl] = status_count.get(rl, 0) + 1
            risk_score = {"CRITICAL": 85.0, "WARNING": 55.0}.get(rl, 20.0)
            level = ha.risk_level(risk_score)
            risk_count[level] = risk_count.get(level, 0) + 1
            sum_risk += risk_score
            sum_rul += asset["lstm_rul_hours"]
            unit_summaries.append(
                {
                    "id": _uuid5_dns(asset["asset_id"]),
                    "code": asset["asset_id"],
                    "jenis_alat_berat_nama": asset["equipment_type"],
                    "status": rl,
                    "health": int(round(100.0 - risk_score)),
                    "risk_score": round(risk_score),
                    "risk_level": level,
                }
            )

        n = max(total, 1)
        status_distribution = [
            {"label": s, "count": status_count.get(s, 0)}
            for s in ["NORMAL", "WARNING", "CRITICAL"]
        ]
        risk_distribution = [
            {"label": s, "count": risk_count.get(s, 0)}
            for s in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        ]
        return {
            "status": "success",
            "mode": "live",
            "data": {
                "total_units": total,
                "avg_health": round(100.0 - sum_risk / n),
                "avg_risk_score": round(sum_risk / n),
                "fleet_avg_suhu": 85.0,
                "fleet_avg_vibration": 2.5,
                "units_at_risk": risk_count.get("HIGH", 0) + risk_count.get("CRITICAL", 0),
                "status_distribution": status_distribution,
                "risk_distribution": risk_distribution,
                "units": unit_summaries,
                "updated_at": _utcnow_iso(),
            },
        }

    # SIMULASI
    rows = await db.fetch(
        """
        SELECT u.*, j.nama as jenis_alat_berat_nama
        FROM unit_tambang u
        LEFT JOIN jenis_alat_berat j ON u.jenis_alat_berat_id = j.id
        ORDER BY u.health ASC
        """
    )
    units = [_row_to_unit(r) for r in rows]
    total = len(units)
    status_count = {}
    risk_count = {}
    sum_health = sum_risk = sum_suhu = sum_vib = 0.0
    unit_summaries = []

    for u in units:
        status_count[u["status"]] = status_count.get(u["status"], 0) + 1
        a = ha.derive_unit_analysis(u)
        risk = float(a["risk_score"])
        level = a["risk_level"]
        risk_count[level] = risk_count.get(level, 0) + 1
        sum_health += u["health"]
        sum_risk += risk
        sum_suhu += float(a["sensor_readings"]["suhu_mesin"])
        sum_vib += float(a["sensor_readings"]["vibration"])
        unit_summaries.append(
            {
                "id": u["id"],
                "code": u["code"],
                "jenis_alat_berat_nama": u.get("jenis_alat_berat_nama"),
                "status": u["status"],
                "health": u["health"],
                "risk_score": risk,
                "risk_level": level,
            }
        )

    n = max(total, 1)
    status_distribution = [
        {"label": s, "count": status_count.get(s, 0)} for s in ["SEHAT", "WARNING", "CRITICAL", "RUSAK"]
    ]
    risk_distribution = [
        {"label": s, "count": risk_count.get(s, 0)} for s in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    ]

    return {
        "status": "success",
        "data": {
            "total_units": total,
            "avg_health": round(sum_health / n),
            "avg_risk_score": round(sum_risk / n),
            "fleet_avg_suhu": round(sum_suhu / n),
            "fleet_avg_vibration": round((sum_vib / n) * 10.0) / 10.0,
            "units_at_risk": risk_count.get("HIGH", 0) + risk_count.get("CRITICAL", 0),
            "status_distribution": status_distribution,
            "risk_distribution": risk_distribution,
            "units": unit_summaries,
            "updated_at": _utcnow_iso(),
        },
    }


@router.get("/unit/{unit_id}", dependencies=[Depends(require_auth)])
async def get_unit_analysis(
    unit_id: str,
    db: PostgresDb = Depends(_get_db),
    state: SharedPratyaksaState = Depends(_get_state),
    client: PratyaksaApiClient = Depends(_get_client),
) -> dict:
    current = await state.read()
    mode = current.mode
    reachable = current.api_reachable

    if mode == PratyaksaMode.LIVE and reachable:
        fleet = [a.model_dump() for a in current.fleet_data]
        asset = None
        for a in fleet:
            expected_uuid = _uuid5_dns(a["asset_id"])
            if a["asset_id"] == unit_id or expected_uuid == unit_id:
                asset = a
                break

        if asset is None:
            raise NotFoundError(f"Unit dengan id {unit_id} tidak ditemukan di LIVE fleet")

        try:
            result = await client.get_result(asset["asset_id"])
        except Exception:
            result = {
                "asset_id": asset["asset_id"],
                "equipment_type": asset["equipment_type"],
                "risk_level": asset["risk_level"],
                "lstm_rul_hours": asset["lstm_rul_hours"],
            }

        risk_score = {"CRITICAL": 85.0, "WARNING": 55.0}.get(asset["risk_level"], 20.0)
        level = ha.risk_level(risk_score)
        rul = asset["lstm_rul_hours"]
        analysis = {
            "unit": {
                "id": _uuid5_dns(asset["asset_id"]),
                "code": asset["asset_id"],
                "jenis_alat_berat_nama": asset["equipment_type"],
                "status": asset["risk_level"],
                "health": int(round(100.0 - risk_score)),
            },
            "risk_score": round(risk_score),
            "risk_level": level,
            "sensor_readings": {
                "suhu_mesin": result.get("engine_oil_temp_c", 85.0),
                "vibration": result.get("vibration_z_g", 2.0),
                "tekanan_oli": result.get("engine_oil_pressure_psi", 55.0),
                "rpm": result.get("engine_rpm", 1500.0),
                "fuel_level": 65.0,
                "oil_particle_iso": result.get("oil_particle_count_iso", 15.0),
                "acoustic_db": result.get("acoustic_emission_db", 50.0),
                "jam_operasi": 5000.0,
            },
            "rul_prediction": {
                "component": "Engine",
                "hours_remaining": rul,
                "lower_bound": round(rul * 0.82),
                "upper_bound": round(rul * 1.18),
                "confidence": 75.0 + min(max(round(asset["rul_uncertainty"] * 10.0), 0.0), 25.0),
            },
            "component_health": [
                {"component": "Engine", "health": round(min(max(100.0 - risk_score, 3.0), 100.0))},
                {"component": "Hidrolik", "health": round(min(max(90.0 - risk_score * 0.5, 3.0), 100.0))},
                {"component": "Transmisi", "health": round(min(max(85.0 - risk_score * 0.4, 3.0), 100.0))},
                {"component": "Rem", "health": round(min(max(80.0 - risk_score * 0.6, 3.0), 100.0))},
                {"component": "Bearing", "health": round(min(max(88.0 - risk_score * 0.5, 3.0), 100.0))},
                {"component": "Kelistrikan", "health": round(min(max(92.0 - risk_score * 0.3, 3.0), 100.0))},
            ],
            "prediction": result,
            "shap_contributions": result.get("shap_values", []) or [],
            "digital_twin": result.get("digital_twin"),
            "drift_status": result.get("drift_status"),
            "updated_at": _utcnow_iso(),
        }
        return {"status": "success", "mode": "live", "data": analysis}

    # SIMULASI
    try:
        uuid.UUID(unit_id)
    except ValueError as exc:
        raise BadRequestError(f"Invalid UUID: {unit_id}") from exc

    row = await db.fetchrow(
        """
        SELECT u.*, j.nama as jenis_alat_berat_nama
        FROM unit_tambang u
        LEFT JOIN jenis_alat_berat j ON u.jenis_alat_berat_id = j.id
        WHERE u.id = $1::uuid
        """,
        unit_id,
    )
    if row is None:
        raise NotFoundError(f"Unit dengan id {unit_id} tidak ditemukan")

    analysis = ha.derive_unit_analysis(_row_to_unit(row))
    return {"status": "success", "mode": "simulasi", "data": analysis}


def _row_to_unit(row) -> dict:
    return {
        "id": str(row["id"]),
        "code": row["code"],
        "jenis_alat_berat_id": str(row["jenis_alat_berat_id"]),
        "jenis_alat_berat_nama": row["jenis_alat_berat_nama"],
        "status": row["status"],
        "health": row["health"],
        "maintenance": row["maintenance"],
        "savings": row["savings"],
        "img_url": row["img_url"],
        "model3d_url": row["model3d_url"],
        "lat": row["lat"],
        "lng": row["lng"],
    }

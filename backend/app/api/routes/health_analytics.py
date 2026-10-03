"""Health Analytics routes: fleet overview & per-unit realtime analysis."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request

from app.core.deps import get_postgres, require_auth
from app.core.errors import BadRequestError, NotFoundError
from app.db.postgres import PostgresDb
from app.services import health_analytics as ha

router = APIRouter(prefix="/analisa", tags=["analisa-health"])


def _get_db(request: Request) -> PostgresDb:
    return get_postgres(request)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/overview", dependencies=[Depends(require_auth)])
async def get_overview(db: PostgresDb = Depends(_get_db)) -> dict:
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
) -> dict:
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

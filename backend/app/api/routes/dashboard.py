"""Dashboard routes: fleet summary + aggregated stats."""

from __future__ import annotations

import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request

from app.core.deps import require_auth
from app.db.postgres import PostgresDb
from app.pratyaksa.state import PratyaksaMode, SharedPratyaksaState

router = APIRouter(tags=["dashboard"])

MONTHS = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Ags", "Sep", "Okt", "Nov", "Des"]
OPERATORS = [
    "OP-Budi S.",
    "OP-Joko P.",
    "OP-Agus T.",
    "OP-Rian M.",
    "OP-Deni R.",
    "OP-Siti N.",
    "OP-Eko W.",
]


def _get_db(request: Request) -> PostgresDb:
    return request.app.state.pg


def _get_state(request: Request) -> SharedPratyaksaState:
    return request.app.state.pratyaksa


def _gen(base: float, early_offset: float, amp: float, phase: float, i: int, last: float) -> int:
    if float(i) >= last:
        return int(min(max(round(base), 0.0), 100.0))
    t = i / last
    wave = math.sin(i * 0.8 + phase) * amp
    v = base + early_offset * (1.0 - t) + wave
    return int(min(max(round(v), 2.0), 98.0))


@router.get("/fleet-summary")
async def get_fleet_summary(db: PostgresDb = Depends(_get_db)) -> dict:
    rows = await db.fetch("SELECT status, COUNT(*) AS count FROM unit_tambang GROUP BY status")
    counts = {"CRITICAL": 0, "WARNING": 0, "SEHAT": 0, "RUSAK": 0}
    total = 0
    for row in rows:
        total += row["count"]
        if row["status"] in counts:
            counts[row["status"]] = row["count"]
    return {
        "status": "success",
        "data": {
            "critical": counts["CRITICAL"],
            "warning": counts["WARNING"],
            "normal": counts["SEHAT"],
            "rusak": counts["RUSAK"],
            "total": total,
        },
    }


@router.get("/dashboard", dependencies=[Depends(require_auth)])
async def get_stats(
    db: PostgresDb = Depends(_get_db),
    state: SharedPratyaksaState = Depends(_get_state),
) -> dict:
    current = await state.read()
    mode = current.mode
    reachable = current.api_reachable

    if mode == PratyaksaMode.LIVE and reachable:
        return _live_stats([a.model_dump() for a in current.fleet_data])

    # SIMULASI mode
    total_units = await db.fetchval("SELECT COUNT(*) FROM unit_tambang")
    active_units = await db.fetchval("SELECT COUNT(*) FROM unit_tambang WHERE status = 'SEHAT'")
    critical_units = await db.fetchval(
        "SELECT COUNT(*) FROM unit_tambang WHERE status IN ('CRITICAL', 'RUSAK')"
    )
    total_savings = await db.fetchval("SELECT COALESCE(CAST(SUM(savings) AS BIGINT), 0) FROM unit_tambang")

    status_rows = await db.fetch(
        "SELECT status, COUNT(*) as count FROM unit_tambang GROUP BY status ORDER BY status"
    )

    label_map = {"SEHAT": "Sehat", "WARNING": "Warning", "CRITICAL": "Critical", "RUSAK": "Rusak"}
    status_distribution = [
        {"label": label_map.get(r["status"], r["status"]), "jumlah": r["count"]} for r in status_rows
    ]

    unit_codes = await db.fetch("SELECT code, status FROM unit_tambang ORDER BY code")
    sehat_units = [c["code"] for c in unit_codes if c["status"] == "SEHAT"]
    warning_units = [c["code"] for c in unit_codes if c["status"] == "WARNING"]
    critical_units_list = [c["code"] for c in unit_codes if c["status"] in ("CRITICAL", "RUSAK")]

    total = max(total_units, 1)
    base_sehat = len(sehat_units) / total * 100.0
    base_warning = len(warning_units) / total * 100.0
    base_critical = len(critical_units_list) / total * 100.0
    last = float(len(MONTHS) - 1)

    monthly_fleet_data = []
    for i, m in enumerate(MONTHS):
        monthly_fleet_data.append(
            {
                "month": m,
                "sehat": {"val": _gen(base_sehat, -16.0, 5.0, 0.0, i, last), "units": sehat_units},
                "warning": {"val": _gen(base_warning, 9.0, 4.0, 1.2, i, last), "units": warning_units},
                "critical": {
                    "val": _gen(base_critical, 11.0, 4.5, 2.4, i, last),
                    "units": critical_units_list,
                },
            }
        )

    map_units = await db.fetch(
        """
        SELECT u.code, j.nama AS jenis, u.status, u.health, u.lat, u.lng
        FROM unit_tambang u
        LEFT JOIN jenis_alat_berat j ON u.jenis_alat_berat_id = j.id
        WHERE u.lat IS NOT NULL AND u.lng IS NOT NULL
        ORDER BY u.code
        """
    )

    map_locations = []
    for i, u in enumerate(map_units):
        color_hex, level = {
            "SEHAT": ("#1FA971", "L"),
            "WARNING": ("#E0A106", "H"),
            "CRITICAL": ("#E0413E", "I"),
            "RUSAK": ("#7A848E", "X"),
        }.get(u["status"], ("#7A848E", "L"))
        h = int(u["health"])
        speed = {"SEHAT": "22 km/h", "WARNING": "12 km/h"}.get(u["status"], "0 km/h")
        map_locations.append(
            {
                "id": i + 1,
                "unit": u["code"],
                "unit_type": u["jenis"] or "Heavy Equipment",
                "lat": u["lat"],
                "lng": u["lng"],
                "status": u["status"],
                "level": level,
                "color_hex": color_hex,
                "fuel": f"{min(max(30 + (h % 70), 5), 99)}%",
                "operator": OPERATORS[i % len(OPERATORS)],
                "speed": speed,
                "temp": f"{78 + ((100 - h) * 40 // 100)}°C",
                "last_update": "Baru saja",
            }
        )

    return {
        "status": "success",
        "mode": "simulasi",
        "data": {
            "total_units": total_units,
            "active_units": active_units,
            "critical_units": critical_units,
            "total_savings": total_savings,
            "status_distribution": status_distribution,
            "monthly_fleet_data": monthly_fleet_data,
            "map_locations": map_locations,
        },
    }


def _live_stats(fleet: list[dict]) -> dict:
    total_units = len(fleet)
    normal = warning = critical = 0
    sum_rul = 0.0
    for asset in fleet:
        rl = asset.get("risk_level")
        if rl == "NORMAL":
            normal += 1
        elif rl == "WARNING":
            warning += 1
        elif rl == "CRITICAL":
            critical += 1
        sum_rul += asset.get("lstm_rul_hours", 0.0)

    status_distribution = [
        {"label": "Sehat", "jumlah": normal},
        {"label": "Warning", "jumlah": warning},
        {"label": "Critical", "jumlah": critical},
    ]

    last = float(len(MONTHS) - 1)
    base_sehat = (normal / total_units * 100.0) if total_units else 0.0
    base_warning = (warning / total_units * 100.0) if total_units else 0.0
    base_critical = (critical / total_units * 100.0) if total_units else 0.0
    unit_codes = [a.get("asset_id", "") for a in fleet]

    monthly_fleet_data = []
    for i, m in enumerate(MONTHS):
        monthly_fleet_data.append(
            {
                "month": m,
                "sehat": {"val": _gen(base_sehat, -16.0, 5.0, 0.0, i, last), "units": unit_codes},
                "warning": {"val": _gen(base_warning, 9.0, 4.0, 1.2, i, last), "units": unit_codes},
                "critical": {"val": _gen(base_critical, 11.0, 4.5, 2.4, i, last), "units": unit_codes},
            }
        )

    map_locations = []
    for i, asset in enumerate(fleet):
        rl = asset.get("risk_level")
        color_hex, level = {
            "NORMAL": ("#1FA971", "L"),
            "WARNING": ("#E0A106", "H"),
            "CRITICAL": ("#E0413E", "I"),
        }.get(rl, ("#7A848E", "L"))
        rul = int(asset.get("lstm_rul_hours", 0.0))
        map_locations.append(
            {
                "id": i + 1,
                "unit": asset.get("asset_id", ""),
                "unit_type": asset.get("equipment_type", ""),
                "lat": -7.0 + i * 0.5,
                "lng": 110.0 + i * 0.3,
                "status": rl,
                "level": level,
                "color_hex": color_hex,
                "fuel": f"{50 + (i * 7) % 40}%",
                "operator": OPERATORS[i % len(OPERATORS)],
                "speed": "22 km/h" if rl == "NORMAL" else "12 km/h",
                "temp": f"{75 + (100 - min(rul, 100)) % 30}°C",
                "last_update": "Baru saja",
            }
        )

    return {
        "status": "success",
        "mode": "live",
        "data": {
            "total_units": total_units,
            "active_units": normal,
            "critical_units": critical,
            "total_savings": 0,
            "status_distribution": status_distribution,
            "monthly_fleet_data": monthly_fleet_data,
            "map_locations": map_locations,
        },
    }


_ = timezone
_ = datetime

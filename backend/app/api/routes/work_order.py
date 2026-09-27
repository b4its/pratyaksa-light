"""Work Order routes (PostgreSQL)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status

from app.core.deps import get_postgres, require_auth
from app.core.errors import NotFoundError, ValidationError
from app.db.postgres import PostgresDb
from app.schemas.work_order import CreateWorkOrderRequest, UpdateWorkOrderRequest

router = APIRouter(prefix="/work-orders", tags=["work-orders"])

WO_NUMBER_EXPR = "'WO-' || LPAD(seq::text, 5, '0') AS wo_number"


def _get_db(request: Request) -> PostgresDb:
    return get_postgres(request)


def _serialize(row) -> dict:
    return {
        "id": str(row["id"]),
        "seq": row["seq"],
        "wo_number": row["wo_number"],
        "asset_code": row["asset_code"],
        "equipment_type": row["equipment_type"],
        "status_unit": row["status_unit"],
        "priority": row["priority"],
        "component": row["component"],
        "part_no": row["part_no"],
        "rul_hours": row["rul_hours"],
        "est_cost": row["est_cost"],
        "scheduled_at": row["scheduled_at"].isoformat() if row["scheduled_at"] else None,
        "est_completion_at": row["est_completion_at"].isoformat() if row["est_completion_at"] else None,
        "technician": row["technician"],
        "notes": row["notes"],
        "feedback": row["feedback"],
        "wo_status": row["wo_status"],
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


def _serialize_unit(row) -> dict:
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
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


@router.get("", dependencies=[Depends(require_auth)])
async def list_items(
    db: PostgresDb = Depends(_get_db),
    page: int | None = Query(None),
    per_page: int | None = Query(None),
    wo_status: str | None = Query(None),
    asset_code: str | None = Query(None),
) -> dict:
    _page = max(page or 1, 1)
    # Cap raised to 500 so the dashboard's "saved work orders" table can load
    # every record for client-side search/pagination/export (the frontend
    # requests per_page=500).
    _per_page = min(per_page or 20, 500)
    offset = (_page - 1) * _per_page

    conditions: list[str] = []
    args: list = []
    idx = 1
    if wo_status:
        conditions.append(f"wo_status = ${idx}")
        args.append(wo_status)
        idx += 1
    if asset_code:
        conditions.append(f"asset_code ILIKE ${idx}")
        args.append(f"%{asset_code}%")
        idx += 1
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    select_sql = (
        f"SELECT *, {WO_NUMBER_EXPR} FROM work_orders {where_clause} "
        f"ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx + 1}"
    )
    count_sql = f"SELECT COUNT(*) FROM work_orders {where_clause}"

    items = await db.fetch(select_sql, *args, _per_page, offset)
    total = await db.fetchval(count_sql, *args)
    total_pages = (total + _per_page - 1) // _per_page

    return {
        "status": "success",
        "data": {
            "data": [_serialize(r) for r in items],
            "total": total,
            "page": _page,
            "per_page": _per_page,
            "total_pages": total_pages,
        },
    }


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_auth)])
async def create(body: CreateWorkOrderRequest, db: PostgresDb = Depends(_get_db)) -> dict:
    valid_status = ["WARNING", "CRITICAL", "RUSAK"]
    if body.status_unit not in valid_status:
        raise ValidationError("status_unit harus salah satu dari: WARNING, CRITICAL, RUSAK")

    if body.priority is not None:
        priority = body.priority
    else:
        priority = "MEDIUM" if body.status_unit == "WARNING" else "HIGH"
    if priority not in ["HIGH", "MEDIUM", "LOW"]:
        raise ValidationError("priority harus salah satu dari: HIGH, MEDIUM, LOW")

    equipment_type = body.equipment_type or "Heavy Equipment"
    component = body.component or "Komponen Utama"
    rul_hours = body.rul_hours if body.rul_hours is not None else 0
    est_cost = body.est_cost if body.est_cost is not None else 0

    row = await db.fetchrow(
        f"""
        INSERT INTO work_orders
            (asset_code, equipment_type, status_unit, priority, component, part_no,
             rul_hours, est_cost, scheduled_at, est_completion_at, technician, notes)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        RETURNING *, {WO_NUMBER_EXPR}
        """,
        body.asset_code,
        equipment_type,
        body.status_unit,
        priority,
        component,
        body.part_no,
        rul_hours,
        est_cost,
        body.scheduled_at,
        body.est_completion_at,
        body.technician,
        body.notes,
    )
    return {"status": "success", "data": _serialize(row)}


@router.get("/{wo_id}", dependencies=[Depends(require_auth)])
async def get_by_id(wo_id: str, db: PostgresDb = Depends(_get_db)) -> dict:
    row = await db.fetchrow(
        f"SELECT *, {WO_NUMBER_EXPR} FROM work_orders WHERE id = $1::uuid", wo_id
    )
    if row is None:
        raise NotFoundError(f"Work order {wo_id} tidak ditemukan")

    unit = await db.fetchrow(
        """
        SELECT u.*, j.nama as jenis_alat_berat_nama
        FROM unit_tambang u
        LEFT JOIN jenis_alat_berat j ON u.jenis_alat_berat_id = j.id
        WHERE u.code ILIKE $1
        """,
        row["asset_code"],
    )
    return {
        "status": "success",
        "data": {
            "work_order": _serialize(row),
            "unit": _serialize_unit(unit) if unit else None,
        },
    }


@router.put("/{wo_id}", dependencies=[Depends(require_auth)])
async def update(
    wo_id: str,
    body: UpdateWorkOrderRequest,
    db: PostgresDb = Depends(_get_db),
) -> dict:
    existing = await db.fetchrow(
        f"SELECT *, {WO_NUMBER_EXPR} FROM work_orders WHERE id = $1::uuid", wo_id
    )
    if existing is None:
        raise NotFoundError(f"Work order {wo_id} tidak ditemukan")

    if body.wo_status is not None and body.wo_status not in [
        "OPEN",
        "IN_PROGRESS",
        "COMPLETED",
        "CANCELLED",
    ]:
        raise ValidationError("wo_status harus: OPEN, IN_PROGRESS, COMPLETED, CANCELLED")
    if body.feedback is not None and body.feedback not in [
        "as_predicted",
        "worse",
        "better",
        "false_alarm",
    ]:
        raise ValidationError("feedback harus: as_predicted, worse, better, false_alarm")

    wo_status = body.wo_status if body.wo_status is not None else existing["wo_status"]
    technician = body.technician if body.technician is not None else existing["technician"]
    notes = body.notes if body.notes is not None else existing["notes"]
    feedback = body.feedback if body.feedback is not None else existing["feedback"]

    row = await db.fetchrow(
        f"""
        UPDATE work_orders
        SET wo_status = $1, technician = $2, notes = $3, feedback = $4, updated_at = NOW()
        WHERE id = $5::uuid
        RETURNING *, {WO_NUMBER_EXPR}
        """,
        wo_status,
        technician,
        notes,
        feedback,
        wo_id,
    )

    if wo_status == "COMPLETED":
        await db.execute(
            """
            UPDATE unit_tambang
            SET status = 'SEHAT',
                health = GREATEST(health, 92),
                maintenance = 'Selesai Perbaikan',
                updated_at = NOW()
            WHERE code ILIKE $1
            """,
            row["asset_code"],
        )

    return {"status": "success", "data": _serialize(row)}

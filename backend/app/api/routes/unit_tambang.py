"""Unit Tambang CRUD routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status

from app.core.deps import require_auth
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.security import new_uuid
from app.db.postgres import PostgresDb
from app.schemas.unit_tambang import (
    UNIT_STATUSES,
    CreateUnitTambangRequest,
    UpdateUnitTambangRequest,
)

router = APIRouter(prefix="/unit-tambang", tags=["unit-tambang"])


def _get_db(request: Request) -> PostgresDb:
    return request.app.state.pg


def _serialize(row) -> dict:
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
    search: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    jenis_alat_berat_id: str | None = Query(None),
) -> dict:
    _page = max(page or 1, 1)
    _per_page = min(per_page or 10, 100)
    offset = (_page - 1) * _per_page

    conditions: list[str] = []
    args: list = []
    idx = 1

    if search:
        conditions.append(f"(u.code ILIKE ${idx} OR j.nama ILIKE ${idx})")
        args.append(f"%{search}%")
        idx += 1
    if status_filter:
        conditions.append(f"u.status = ${idx}")
        args.append(status_filter)
        idx += 1
    if jenis_alat_berat_id:
        conditions.append(f"u.jenis_alat_berat_id = ${idx}::uuid")
        args.append(jenis_alat_berat_id)
        idx += 1

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    base = f"FROM unit_tambang u LEFT JOIN jenis_alat_berat j ON u.jenis_alat_berat_id = j.id {where_clause}"

    select_sql = f"SELECT u.*, j.nama as jenis_alat_berat_nama {base} ORDER BY u.created_at DESC LIMIT ${idx} OFFSET ${idx + 1}"
    count_sql = f"SELECT COUNT(*) {base}"

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
async def create(body: CreateUnitTambangRequest, db: PostgresDb = Depends(_get_db)) -> dict:
    if body.status not in UNIT_STATUSES:
        raise ValidationError("Status harus salah satu dari: SEHAT, WARNING, CRITICAL, RUSAK")

    jenis_exists = await db.fetchval(
        "SELECT COUNT(*) FROM jenis_alat_berat WHERE id = $1::uuid", body.jenis_alat_berat_id
    )
    if not jenis_exists:
        raise NotFoundError("Jenis alat berat tidak ditemukan")

    code_exists = await db.fetchval(
        "SELECT COUNT(*) FROM unit_tambang WHERE code ILIKE $1", body.code
    )
    if code_exists and code_exists > 0:
        raise ConflictError("Kode unit sudah terdaftar")

    row = await db.fetchrow(
        """
        WITH inserted AS (
            INSERT INTO unit_tambang
                (id, code, jenis_alat_berat_id, status, health, maintenance, savings,
                 img_url, model3d_url, lat, lng, created_at, updated_at)
            VALUES ($1, $2, $3::uuid, $4, $5, $6, $7, $8, $9, $10, $11, NOW(), NOW())
            RETURNING *
        )
        SELECT i.*, j.nama as jenis_alat_berat_nama
        FROM inserted i
        LEFT JOIN jenis_alat_berat j ON i.jenis_alat_berat_id = j.id
        """,
        new_uuid(),
        body.code,
        body.jenis_alat_berat_id,
        body.status,
        body.health,
        body.maintenance,
        body.savings,
        body.img_url,
        body.model3d_url,
        body.lat,
        body.lng,
    )
    return {"status": "success", "data": _serialize(row)}


@router.get("/{unit_id}", dependencies=[Depends(require_auth)])
async def get_by_id(unit_id: str, db: PostgresDb = Depends(_get_db)) -> dict:
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
        raise NotFoundError(f"Unit tambang dengan id {unit_id} tidak ditemukan")
    return {"status": "success", "data": _serialize(row)}


@router.put("/{unit_id}", dependencies=[Depends(require_auth)])
async def update(
    unit_id: str,
    body: UpdateUnitTambangRequest,
    db: PostgresDb = Depends(_get_db),
) -> dict:
    existing = await db.fetchrow(
        """
        SELECT u.*, j.nama as jenis_alat_berat_nama
        FROM unit_tambang u
        LEFT JOIN jenis_alat_berat j ON u.jenis_alat_berat_id = j.id
        WHERE u.id = $1::uuid
        """,
        unit_id,
    )
    if existing is None:
        raise NotFoundError(f"Unit tambang dengan id {unit_id} tidak ditemukan")

    if body.status is not None and body.status not in UNIT_STATUSES:
        raise ValidationError("Status harus salah satu dari: SEHAT, WARNING, CRITICAL, RUSAK")

    code = body.code if body.code is not None else existing["code"]
    jenis_id = (
        body.jenis_alat_berat_id
        if body.jenis_alat_berat_id is not None
        else str(existing["jenis_alat_berat_id"])
    )
    status = body.status if body.status is not None else existing["status"]
    health = body.health if body.health is not None else existing["health"]
    maintenance = body.maintenance if body.maintenance is not None else existing["maintenance"]
    savings = body.savings if body.savings is not None else existing["savings"]
    img_url = body.img_url if body.img_url is not None else existing["img_url"]
    model3d_url = body.model3d_url if body.model3d_url is not None else existing["model3d_url"]
    lat = body.lat if body.lat is not None else existing["lat"]
    lng = body.lng if body.lng is not None else existing["lng"]

    row = await db.fetchrow(
        """
        WITH updated AS (
            UPDATE unit_tambang
            SET code = $1, jenis_alat_berat_id = $2::uuid, status = $3, health = $4,
                maintenance = $5, savings = $6, img_url = $7, model3d_url = $8,
                lat = $9, lng = $10, updated_at = NOW()
            WHERE id = $11::uuid
            RETURNING *
        )
        SELECT u.*, j.nama as jenis_alat_berat_nama
        FROM updated u
        LEFT JOIN jenis_alat_berat j ON u.jenis_alat_berat_id = j.id
        """,
        code,
        jenis_id,
        status,
        health,
        maintenance,
        savings,
        img_url,
        model3d_url,
        lat,
        lng,
        unit_id,
    )
    return {"status": "success", "data": _serialize(row)}


@router.delete("/{unit_id}", dependencies=[Depends(require_auth)])
async def delete(unit_id: str, db: PostgresDb = Depends(_get_db)) -> dict:
    result = await db.execute("DELETE FROM unit_tambang WHERE id = $1::uuid", unit_id)
    if result.endswith(" 0"):
        raise NotFoundError(f"Unit tambang dengan id {unit_id} tidak ditemukan")
    return {"status": "success", "message": "Unit tambang berhasil dihapus"}

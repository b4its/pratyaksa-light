"""Jenis Alat Berat CRUD routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status

from app.core.deps import get_postgres, require_auth
from app.core.errors import ConflictError, NotFoundError
from app.core.security import new_uuid
from app.db.postgres import PostgresDb
from app.schemas.jenis_alat_berat import (
    CreateJenisAlatBeratRequest,
    UpdateJenisAlatBeratRequest,
)

router = APIRouter(prefix="/jenis-alat-berat", tags=["jenis-alat-berat"])


def _get_db(request: Request) -> PostgresDb:
    return get_postgres(request)


def _serialize(row) -> dict:
    return {
        "id": str(row["id"]),
        "nama": row["nama"],
        "deskripsi": row["deskripsi"],
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


@router.get("", dependencies=[Depends(require_auth)])
async def list_items(
    db: PostgresDb = Depends(_get_db),
    page: int | None = Query(None),
    per_page: int | None = Query(None),
    search: str | None = Query(None),
) -> dict:
    _page = max(page or 1, 1)
    _per_page = min(per_page or 10, 100)
    offset = (_page - 1) * _per_page

    if search:
        pattern = f"%{search}%"
        items = await db.fetch(
            "SELECT * FROM jenis_alat_berat WHERE nama ILIKE $1 ORDER BY nama ASC LIMIT $2 OFFSET $3",
            pattern,
            _per_page,
            offset,
        )
        total = await db.fetchval(
            "SELECT COUNT(*) FROM jenis_alat_berat WHERE nama ILIKE $1", pattern
        )
    else:
        items = await db.fetch(
            "SELECT * FROM jenis_alat_berat ORDER BY nama ASC LIMIT $1 OFFSET $2",
            _per_page,
            offset,
        )
        total = await db.fetchval("SELECT COUNT(*) FROM jenis_alat_berat")

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
async def create(body: CreateJenisAlatBeratRequest, db: PostgresDb = Depends(_get_db)) -> dict:
    existing = await db.fetchval(
        "SELECT COUNT(*) FROM jenis_alat_berat WHERE nama ILIKE $1", body.nama
    )
    if existing and existing > 0:
        raise ConflictError("Jenis alat berat dengan nama tersebut sudah ada")

    row = await db.fetchrow(
        """
        INSERT INTO jenis_alat_berat (id, nama, deskripsi, created_at, updated_at)
        VALUES ($1, $2, $3, NOW(), NOW())
        RETURNING *
        """,
        new_uuid(),
        body.nama,
        body.deskripsi,
    )
    return {"status": "success", "data": _serialize(row)}


@router.get("/{item_id}", dependencies=[Depends(require_auth)])
async def get_by_id(item_id: str, db: PostgresDb = Depends(_get_db)) -> dict:
    row = await db.fetchrow("SELECT * FROM jenis_alat_berat WHERE id = $1::uuid", item_id)
    if row is None:
        raise NotFoundError(f"Jenis alat berat dengan id {item_id} tidak ditemukan")
    return {"status": "success", "data": _serialize(row)}


@router.put("/{item_id}", dependencies=[Depends(require_auth)])
async def update(
    item_id: str,
    body: UpdateJenisAlatBeratRequest,
    db: PostgresDb = Depends(_get_db),
) -> dict:
    existing = await db.fetchrow("SELECT * FROM jenis_alat_berat WHERE id = $1::uuid", item_id)
    if existing is None:
        raise NotFoundError(f"Jenis alat berat dengan id {item_id} tidak ditemukan")

    nama = body.nama if body.nama is not None else existing["nama"]
    deskripsi = body.deskripsi if body.deskripsi is not None else existing["deskripsi"]

    row = await db.fetchrow(
        """
        UPDATE jenis_alat_berat
        SET nama = $1, deskripsi = $2, updated_at = NOW()
        WHERE id = $3::uuid
        RETURNING *
        """,
        nama,
        deskripsi,
        item_id,
    )
    return {"status": "success", "data": _serialize(row)}


@router.delete("/{item_id}", dependencies=[Depends(require_auth)])
async def delete(item_id: str, db: PostgresDb = Depends(_get_db)) -> dict:
    referenced = await db.fetchval(
        "SELECT COUNT(*) FROM unit_tambang WHERE jenis_alat_berat_id = $1::uuid", item_id
    )
    if referenced and referenced > 0:
        raise ConflictError(
            "Tidak bisa menghapus jenis alat berat yang sedang digunakan oleh unit"
        )

    result = await db.execute("DELETE FROM jenis_alat_berat WHERE id = $1::uuid", item_id)
    if result.endswith(" 0"):
        raise NotFoundError(f"Jenis alat berat dengan id {item_id} tidak ditemukan")
    return {"status": "success", "message": "Jenis alat berat berhasil dihapus"}

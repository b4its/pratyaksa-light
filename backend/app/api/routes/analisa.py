"""Analisa Kerusakan routes (MongoDB, flexible schema)."""

from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, Query, Request, status

from app.core.deps import get_mongo, require_auth
from app.core.errors import BadRequestError, InternalError, NotFoundError, ValidationError
from app.db.mongo import MongoDb
from app.schemas.analisa import CreateAnalisaRequest, UpdateAnalisaRequest

router = APIRouter(prefix="/analisa", tags=["analisa"])

COLLECTION = "analisa_kerusakan"
VALID_SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
VALID_STATUSES = ["OPEN", "IN_PROGRESS", "RESOLVED"]


def _get_mongo(request: Request) -> MongoDb:
    return get_mongo(request)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc["_id"] = str(doc["_id"])
    for key in ("created_at", "updated_at"):
        if isinstance(doc.get(key), datetime):
            doc[key] = doc[key].isoformat()
    sensor = doc.get("sensor_data")
    if isinstance(sensor, dict) and isinstance(sensor.get("timestamp"), datetime):
        sensor["timestamp"] = sensor["timestamp"].isoformat()
    return doc


@router.get("", dependencies=[Depends(require_auth)])
async def list_items(
    mongo: MongoDb = Depends(_get_mongo),
    page: int | None = Query(None),
    per_page: int | None = Query(None),
    unit_tambang_id: str | None = Query(None),
    severity: str | None = Query(None),
    status_analisa: str | None = Query(None),
) -> dict:
    _page = max(page or 1, 1)
    _per_page = min(per_page or 10, 100)
    skip = (_page - 1) * _per_page

    query: dict = {}
    if unit_tambang_id:
        query["unit_tambang_id"] = unit_tambang_id
    if severity:
        query["severity"] = severity
    if status_analisa:
        query["status_analisa"] = status_analisa

    coll = mongo.collection(COLLECTION)
    total = await coll.count_documents(query)
    cursor = coll.find(query).sort("created_at", -1).skip(skip).limit(_per_page)
    items = await cursor.to_list(length=_per_page)

    total_pages = (total + _per_page - 1) // _per_page
    return {
        "status": "success",
        "data": {
            "data": [_serialize(d) for d in items],
            "total": total,
            "page": _page,
            "per_page": _per_page,
            "total_pages": total_pages,
        },
    }


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_auth)])
async def create(body: CreateAnalisaRequest, mongo: MongoDb = Depends(_get_mongo)) -> dict:
    if body.severity not in VALID_SEVERITIES:
        raise ValidationError("Severity harus: LOW, MEDIUM, HIGH, atau CRITICAL")

    now = _utcnow()
    doc = {
        "unit_tambang_id": body.unit_tambang_id,
        "unit_code": body.unit_code,
        "tipe_kerusakan": body.tipe_kerusakan,
        "deskripsi": body.deskripsi,
        "severity": body.severity,
        "sensor_data": {
            "suhu_mesin": body.sensor_data.suhu_mesin,
            "tekanan_oli": body.sensor_data.tekanan_oli,
            "rpm": body.sensor_data.rpm,
            "fuel_level": body.sensor_data.fuel_level,
            "vibration": body.sensor_data.vibration,
            "jam_operasi": body.sensor_data.jam_operasi,
            "timestamp": now,
        },
        "rekomendasi": body.rekomendasi,
        "status_analisa": "OPEN",
        "dilaporkan_oleh": body.dilaporkan_oleh,
        "created_at": now,
        "updated_at": now,
    }

    coll = mongo.collection(COLLECTION)
    result = await coll.insert_one(doc)
    created = await coll.find_one({"_id": result.inserted_id})
    if created is None:
        raise InternalError("Failed to fetch created document")
    return {"status": "success", "data": _serialize(created)}


@router.get("/{item_id}", dependencies=[Depends(require_auth)])
async def get_by_id(item_id: str, mongo: MongoDb = Depends(_get_mongo)) -> dict:
    try:
        oid = ObjectId(item_id)
    except Exception as exc:
        raise BadRequestError("ID tidak valid") from exc
    coll = mongo.collection(COLLECTION)
    doc = await coll.find_one({"_id": oid})
    if doc is None:
        raise NotFoundError(f"Analisa dengan id {item_id} tidak ditemukan")
    return {"status": "success", "data": _serialize(doc)}


@router.put("/{item_id}", dependencies=[Depends(require_auth)])
async def update(
    item_id: str,
    body: UpdateAnalisaRequest,
    mongo: MongoDb = Depends(_get_mongo),
) -> dict:
    try:
        oid = ObjectId(item_id)
    except Exception as exc:
        raise BadRequestError("ID tidak valid") from exc

    coll = mongo.collection(COLLECTION)
    existing = await coll.find_one({"_id": oid})
    if existing is None:
        raise NotFoundError(f"Analisa dengan id {item_id} tidak ditemukan")

    update_doc: dict = {"updated_at": _utcnow()}
    if body.status_analisa is not None:
        if body.status_analisa not in VALID_STATUSES:
            raise ValidationError("Status analisa harus: OPEN, IN_PROGRESS, atau RESOLVED")
        update_doc["status_analisa"] = body.status_analisa
    if body.rekomendasi is not None:
        update_doc["rekomendasi"] = body.rekomendasi
    if body.deskripsi is not None:
        update_doc["deskripsi"] = body.deskripsi

    await coll.update_one({"_id": oid}, {"$set": update_doc})
    updated = await coll.find_one({"_id": oid})
    if updated is None:
        raise InternalError("Failed to fetch updated document")
    return {"status": "success", "data": _serialize(updated)}


@router.delete("/{item_id}", dependencies=[Depends(require_auth)])
async def delete(item_id: str, mongo: MongoDb = Depends(_get_mongo)) -> dict:
    try:
        oid = ObjectId(item_id)
    except Exception as exc:
        raise BadRequestError("ID tidak valid") from exc
    coll = mongo.collection(COLLECTION)
    result = await coll.delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise NotFoundError(f"Analisa dengan id {item_id} tidak ditemukan")
    return {"status": "success", "message": "Analisa berhasil dihapus"}

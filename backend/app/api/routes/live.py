"""Live data routes (MongoDB) — predictions, fleet, work orders, stats."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request

from app.core.errors import NotFoundError
from app.db.mongo import MongoDb

router = APIRouter(prefix="/live", tags=["live"])


def _get_mongo(request: Request) -> MongoDb:
    return request.app.state.mongo


def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc.pop("_id", None)
    if isinstance(doc.get("stored_at"), datetime):
        doc["stored_at"] = doc["stored_at"].isoformat()
    return doc


@router.get("/predictions")
async def list_predictions(
    mongo: MongoDb = Depends(_get_mongo),
    limit: int | None = Query(None),
    asset_id: str | None = Query(None),
) -> dict:
    _limit = min(limit or 50, 500)
    query = {"asset_id": asset_id} if asset_id else {}
    coll = mongo.collection("live_predictions")
    cursor = coll.find(query).sort("stored_at", -1).limit(_limit)
    items = await cursor.to_list(length=_limit)
    return {"status": "success", "data": [_serialize(d) for d in items], "total": len(items)}


@router.get("/predictions/{asset_id}/latest")
async def get_latest_prediction(asset_id: str, mongo: MongoDb = Depends(_get_mongo)) -> dict:
    coll = mongo.collection("live_predictions")
    cursor = coll.find({"asset_id": asset_id}).sort("stored_at", -1).limit(1)
    items = await cursor.to_list(length=1)
    if not items:
        raise NotFoundError(f"Prediction untuk asset {asset_id} tidak ditemukan")
    return {"status": "success", "data": _serialize(items[0])}


@router.get("/fleet")
async def list_fleet_snapshots(
    mongo: MongoDb = Depends(_get_mongo),
    limit: int | None = Query(None),
    asset_id: str | None = Query(None),
) -> dict:
    _limit = min(limit or 100, 1000)
    query = {"asset_id": asset_id} if asset_id else {}
    coll = mongo.collection("live_fleet_snapshots")
    cursor = coll.find(query).sort("stored_at", -1).limit(_limit)
    items = await cursor.to_list(length=_limit)
    return {"status": "success", "data": [_serialize(d) for d in items], "total": len(items)}


@router.get("/work-orders")
async def list_work_orders(
    mongo: MongoDb = Depends(_get_mongo),
    limit: int | None = Query(None),
    asset_id: str | None = Query(None),
) -> dict:
    _limit = min(limit or 50, 500)
    query = {"asset_id": asset_id} if asset_id else {}
    coll = mongo.collection("live_work_orders")
    cursor = coll.find(query).sort("stored_at", -1).limit(_limit)
    items = await cursor.to_list(length=_limit)
    return {"status": "success", "data": [_serialize(d) for d in items], "total": len(items)}


@router.get("/stats")
async def get_live_stats(mongo: MongoDb = Depends(_get_mongo)) -> dict:
    pred_coll = mongo.collection("live_predictions")
    fleet_coll = mongo.collection("live_fleet_snapshots")
    wo_coll = mongo.collection("live_work_orders")

    total_predictions = await pred_coll.count_documents({})
    total_fleet = await fleet_coll.count_documents({})
    total_work_orders = await wo_coll.count_documents({})

    cutoff = datetime.now(timezone.utc).timestamp() - 3600
    recent_predictions = await pred_coll.count_documents({"processed_at": {"$gte": cutoff}})
    critical_count = await pred_coll.count_documents({"risk_level": "CRITICAL"})

    return {
        "status": "success",
        "data": {
            "total_predictions": total_predictions,
            "total_fleet_snapshots": total_fleet,
            "total_work_orders": total_work_orders,
            "predictions_last_hour": recent_predictions,
            "critical_predictions": critical_count,
        },
    }

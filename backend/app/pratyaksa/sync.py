"""Background sync task: migrate data from ml-pratyaksa PostgreSQL → MongoDB.

Mirrors ``backend_rust/src/pratyaksa/sync.rs``.  Runs every
``ml_sync_interval_secs`` and only when in LIVE mode with a reachable API.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

import asyncpg

from app.core.config import AppConfig
from app.db.mongo import MongoDb
from app.pratyaksa.state import PratyaksaMode, SharedPratyaksaState

logger = logging.getLogger("pratyaksa.sync")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def _sync_predictions(pool: asyncpg.Pool, mongo: MongoDb) -> None:
    rows = await pool.fetch(
        """
        SELECT
            time, asset_id, equipment_type,
            xgb_anomaly_class, xgb_anomaly_label,
            lstm_rul_hours, rul_uncertainty,
            rul_hydraulic_system, rul_hydraulic_pump, rul_pump_seal_main,
            rul_brake_system, rul_brake_caliper, rul_brake_pad_rear,
            rul_steering_system,
            risk_level, risk_class, model_agreement,
            brake_twin_rul, bearing_twin_rul, hydraulic_twin_rul,
            drift_detected, drift_max_z_score, drift_n_features,
            latency_ms, api_version
        FROM predictions
        WHERE time > NOW() - INTERVAL '1 hour'
        ORDER BY time DESC
        LIMIT 500
        """
    )
    now = _utcnow()
    for row in rows:
        mongo.store_prediction(
            {
                "asset_id": row["asset_id"],
                "equipment_type": row["equipment_type"] or "",
                "timestamp": row["time"].isoformat() if row["time"] else "",
                "xgb_anomaly_class": int(row["xgb_anomaly_class"] or 0),
                "xgb_anomaly_label": row["xgb_anomaly_label"] or "",
                "lstm_rul_hours": float(row["lstm_rul_hours"] or 0.0),
                "rul_uncertainty": float(row["rul_uncertainty"] or 0.0),
                "risk_level": row["risk_level"] or "",
                "risk_class": int(row["risk_class"] or 0),
                "model_agreement": bool(row["model_agreement"] or False),
                "RUL_hydraulic_system": float(row["rul_hydraulic_system"] or 0.0),
                "RUL_hydraulic_pump": float(row["rul_hydraulic_pump"] or 0.0),
                "RUL_pump_seal_main": float(row["rul_pump_seal_main"] or 0.0),
                "RUL_brake_system": float(row["rul_brake_system"] or 0.0),
                "RUL_brake_caliper": float(row["rul_brake_caliper"] or 0.0),
                "RUL_brake_pad_rear": float(row["rul_brake_pad_rear"] or 0.0),
                "RUL_steering_system": float(row["rul_steering_system"] or 0.0),
                "digital_twin": {
                    "brake_twin_rul": float(row["brake_twin_rul"] or 0.0),
                    "bearing_twin_rul": float(row["bearing_twin_rul"] or 0.0),
                    "hydraulic_twin_rul": float(row["hydraulic_twin_rul"] or 0.0),
                },
                "drift_status": {
                    "drift_detected": bool(row["drift_detected"] or False),
                    "drifted_features": [],
                    "max_z_score": float(row["drift_max_z_score"] or 0.0),
                    "n_drifted": int(row["drift_n_features"] or 0),
                },
                "processed_at": row["time"].timestamp() if row["time"] else 0.0,
                "latency_ms": float(row["latency_ms"] or 0.0),
                "stored_at": now,
            }
        )
    if rows:
        logger.info("Sync: %d predictions dari ML PostgreSQL", len(rows))


async def _sync_equipment_units(pool: asyncpg.Pool, mongo: MongoDb) -> None:
    rows = await pool.fetch(
        "SELECT asset_id, equipment_type, is_active FROM equipment_units WHERE is_active = TRUE"
    )
    now = _utcnow()
    for row in rows:
        mongo.store_fleet_snapshot(
            {
                "asset_id": row["asset_id"],
                "equipment_type": row["equipment_type"],
                "risk_level": "UNKNOWN",
                "lstm_rul_hours": 0.0,
                "rul_uncertainty": 0.0,
                "model_agreement": True,
                "drift_detected": False,
                "processed_at": now.timestamp(),
                "stored_at": now,
            }
        )
    if rows:
        logger.info("Sync: %d equipment units dari ML PostgreSQL", len(rows))


async def _sync_work_orders(pool: asyncpg.Pool, mongo: MongoDb) -> None:
    rows = await pool.fetch(
        """
        SELECT id, asset_id, component, status, created_at, estimated_cost_usd
        FROM work_orders
        WHERE created_at > NOW() - INTERVAL '24 hours'
        ORDER BY created_at DESC
        LIMIT 200
        """
    )
    now = _utcnow()
    for row in rows:
        mongo.store_work_order(
            {
                "work_order_id": row["id"],
                "asset_id": row["asset_id"],
                "component": row["component"] or "",
                "risk_score": float(row["estimated_cost_usd"] or 0.0) / 1000.0,
                "status": row["status"] or "",
                "created_at": row["created_at"].isoformat() if row["created_at"] else "",
                "stored_at": now,
            }
        )
    if rows:
        logger.info("Sync: %d work orders dari ML PostgreSQL", len(rows))


async def _sync_drift_logs(pool: asyncpg.Pool, mongo: MongoDb) -> None:
    rows = await pool.fetch(
        """
        SELECT asset_id, equipment_type, drifted_features, max_z_score, n_drifted, logged_at
        FROM drift_log
        WHERE logged_at > NOW() - INTERVAL '1 hour'
        ORDER BY logged_at DESC
        LIMIT 200
        """
    )
    now = _utcnow()
    for row in rows:
        features_raw = row["drifted_features"]
        if isinstance(features_raw, str):
            try:
                features = json.loads(features_raw)
            except Exception:
                features = []
        else:
            features = features_raw or []
        mongo.store_drift_log(
            {
                "asset_id": row["asset_id"] or "",
                "equipment_type": row["equipment_type"] or "",
                "drifted_features": features,
                "max_z_score": float(row["max_z_score"] or 0.0),
                "n_drifted": int(row["n_drifted"] or 0),
                "drift_detected": int(row["n_drifted"] or 0) > 0,
                "logged_at": row["logged_at"].isoformat() if row["logged_at"] else "",
                "stored_at": now,
            }
        )
    if rows:
        logger.info("Sync: %d drift logs dari ML PostgreSQL", len(rows))


async def start_sync(state: SharedPratyaksaState, config: AppConfig, mongo: MongoDb) -> None:
    ml_pg_url = config.ml_postgres_url
    interval_secs = config.ml_sync_interval_secs
    logger.info("ML PRATYAKSA Sync dimulai — target: %s (interval: %ss)", ml_pg_url, interval_secs)

    pool: asyncpg.Pool | None = None
    while pool is None:
        try:
            pool = await asyncpg.create_pool(dsn=ml_pg_url, min_size=1, max_size=5, command_timeout=15)
            logger.info("ML PRATYAKSA PostgreSQL terhubung untuk sync")
        except Exception as exc:
            logger.warning("ML PRATYAKSA PostgreSQL tidak tersedia: %s. Sync akan retry.", exc)
            await asyncio.sleep(interval_secs)

    while True:
        await asyncio.sleep(interval_secs)

        current = await state.read()
        if current.mode != PratyaksaMode.LIVE or not current.api_reachable:
            continue

        for name, fn in (
            ("predictions", _sync_predictions),
            ("equipment units", _sync_equipment_units),
            ("work orders", _sync_work_orders),
            ("drift logs", _sync_drift_logs),
        ):
            try:
                await fn(pool, mongo)
            except Exception as exc:
                logger.warning("Sync %s gagal: %s", name, exc)

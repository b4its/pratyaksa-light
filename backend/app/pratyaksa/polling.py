"""Background polling task for the external PRATYAKSA ML API.

Mirrors ``backend_rust/src/pratyaksa/mod.rs::start_polling``.  Honours a manual
mode lock: when the user has set a mode, polling will not override it — only
fill fleet data.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from app.db.mongo import MongoDb
from app.pratyaksa.simulator import generate_fleet
from app.pratyaksa.state import (
    PratyaksaApiClient,
    PratyaksaMode,
    SharedPratyaksaState,
)

logger = logging.getLogger("pratyaksa.polling")


def _now() -> float:
    """Epoch seconds (used for state timestamps)."""
    return datetime.now(timezone.utc).timestamp()


def _dt() -> datetime:
    """Timezone-aware datetime (used for Mongo ``stored_at``)."""
    return datetime.now(timezone.utc)


def store_result_to_mongo(mongo: MongoDb, result: dict[str, Any], now: datetime) -> None:
    """Parse an ML API result JSON into a prediction doc and enqueue it."""
    asset_id = result.get("asset_id", "unknown")
    equipment_type = result.get("equipment_type", "unknown")

    dt = result.get("digital_twin", {}) or {}
    ds = result.get("drift_status", {}) or {}

    prediction = {
        "asset_id": asset_id,
        "equipment_type": equipment_type,
        "timestamp": result.get("timestamp", ""),
        "xgb_anomaly_class": int(result.get("xgb_anomaly_class", 0)),
        "xgb_anomaly_label": result.get("xgb_anomaly_label", "NORMAL"),
        "lstm_rul_hours": float(result.get("lstm_rul_hours", 0.0)),
        "rul_uncertainty": float(result.get("rul_uncertainty", 0.0)),
        "risk_level": result.get("risk_level", "NORMAL"),
        "risk_class": int(result.get("risk_class", 0)),
        "model_agreement": bool(result.get("model_agreement", True)),
        "RUL_hydraulic_system": float(result.get("RUL_hydraulic_system", 0.0)),
        "RUL_hydraulic_pump": float(result.get("RUL_hydraulic_pump", 0.0)),
        "RUL_pump_seal_main": float(result.get("RUL_pump_seal_main", 0.0)),
        "RUL_brake_system": float(result.get("RUL_brake_system", 0.0)),
        "RUL_brake_caliper": float(result.get("RUL_brake_caliper", 0.0)),
        "RUL_brake_pad_rear": float(result.get("RUL_brake_pad_rear", 0.0)),
        "RUL_steering_system": float(result.get("RUL_steering_system", 0.0)),
        "digital_twin": {
            "brake_twin_rul": float(dt.get("brake_twin_rul", 0.0)),
            "bearing_twin_rul": float(dt.get("bearing_twin_rul", 0.0)),
            "hydraulic_twin_rul": float(dt.get("hydraulic_twin_rul", 0.0)),
        },
        "drift_status": {
            "drift_detected": bool(ds.get("drift_detected", False)),
            "drifted_features": ds.get("drifted_features", []) or [],
            "max_z_score": float(ds.get("max_z_score", 0.0)),
            "n_drifted": int(ds.get("n_drifted", 0)),
        },
        "processed_at": float(result.get("processed_at", 0.0)),
        "latency_ms": float(result.get("latency_ms", 0.0)),
        "stored_at": now,
    }
    mongo.store_prediction(prediction)

    if ds.get("drift_detected"):
        mongo.store_drift_log(
            {
                "asset_id": asset_id,
                "equipment_type": equipment_type,
                "drifted_features": ds.get("drifted_features", []) or [],
                "max_z_score": float(ds.get("max_z_score", 0.0)),
                "n_drifted": int(ds.get("n_drifted", 0)),
                "drift_detected": True,
                "logged_at": result.get("timestamp", ""),
                "stored_at": now,
            }
        )


async def _poll_live(state: SharedPratyaksaState, client: PratyaksaApiClient, mongo: MongoDb) -> None:
    """Perform a live poll cycle: health → fleet → per-asset results."""
    try:
        health = await client.check_health()
        await state.update(
            mode=PratyaksaMode.LIVE,
            health_status=health,
            last_health_check=_now(),
            api_reachable=True,
        )
    except Exception as exc:
        logger.warning("Health check gagal: %s", exc)
        await state.update(
            mode=PratyaksaMode.SIMULASI,
            api_reachable=False,
            last_health_check=_now(),
            fleet_data=generate_fleet(),
            last_fleet_poll=_now(),
        )
        return

    try:
        fleet_resp = await client.get_fleet()
        epoch = _now()
        now_dt = _dt()
        asset_ids: list[str] = []

        def _apply(s):
            s.fleet_data = fleet_resp.fleet
            s.last_fleet_poll = epoch
            for asset in fleet_resp.fleet:
                mongo.store_fleet_snapshot(
                    {
                        "asset_id": asset.asset_id,
                        "equipment_type": asset.equipment_type,
                        "risk_level": asset.risk_level,
                        "lstm_rul_hours": asset.lstm_rul_hours,
                        "rul_uncertainty": asset.rul_uncertainty,
                        "model_agreement": asset.model_agreement,
                        "drift_detected": asset.drift_detected,
                        "processed_at": asset.processed_at,
                        "stored_at": now_dt,
                    }
                )
            s.fleet_snapshots_stored += len(fleet_resp.fleet)
            asset_ids.extend(a.asset_id for a in fleet_resp.fleet)

        await state.mutate(_apply)

        for asset_id in asset_ids:
            try:
                result = await client.get_result(asset_id)
                store_result_to_mongo(mongo, result, now_dt)
                await state.mutate(lambda s: setattr(s, "predictions_stored", s.predictions_stored + 1))
            except Exception as exc:  # pragma: no cover
                logger.warning("Result fetch gagal untuk %s: %s", asset_id, exc)
    except Exception as exc:
        logger.warning("Fleet fetch gagal: %s", exc)
        await state.update(fleet_data=generate_fleet(), last_fleet_poll=_now())


async def start_polling(
    state: SharedPratyaksaState,
    client: PratyaksaApiClient,
    poll_interval_secs: int,
    mongo: MongoDb,
) -> None:
    logger.info(
        "PRATYAKSA Polling dimulai — target: %s (interval: %ss)",
        client.base_url,
        poll_interval_secs,
    )
    # Seed simulation data immediately so first requests have data.
    await state.update(
        fleet_data=generate_fleet(),
        last_fleet_poll=_now(),
        last_health_check=_now(),
        polling_active=True,
    )

    while True:
        await asyncio.sleep(poll_interval_secs)

        current = await state.read()
        manual = current.manual_mode

        if manual == PratyaksaMode.SIMULASI:
            def _sim(s):
                s.mode = PratyaksaMode.SIMULASI
                s.api_reachable = False
                s.fleet_data = generate_fleet()
                s.last_fleet_poll = _now()
                s.last_health_check = _now()

            await state.mutate(_sim)
        elif manual == PratyaksaMode.LIVE:
            await _poll_live(state, client, mongo)
        else:
            await _poll_live_auto(state, client, mongo)


async def _poll_live_auto(state: SharedPratyaksaState, client: PratyaksaApiClient, mongo: MongoDb) -> None:
    """Auto mode: detects reachability and switches between live/simulation."""
    await _poll_live(state, client, mongo)

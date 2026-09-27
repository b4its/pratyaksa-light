"""PRATYAKSA ML API proxy/simulator routes."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.core.errors import BadRequestError
from app.pratyaksa import simulator
from app.pratyaksa.state import (
    PratyaksaApiClient,
    PratyaksaMode,
    SharedPratyaksaState,
)
from app.schemas.pratyaksa import ModeSwitchRequest, PredictRequest

router = APIRouter(prefix="/pratyaksa", tags=["pratyaksa"])


def _get_state(request: Request) -> SharedPratyaksaState:
    return request.app.state.pratyaksa


def _get_client(request: Request) -> PratyaksaApiClient:
    return request.app.state.pratyaksa_client


@router.get("/status")
async def get_status(state: SharedPratyaksaState = Depends(_get_state)) -> dict:
    s = await state.read()
    return {
        "status": "success",
        "data": {
            "mode": s.mode.value,
            "manual_mode": s.manual_mode.value if s.manual_mode else None,
            "api_reachable": s.api_reachable,
            "fleet_count": len(s.fleet_data),
            "last_health_check": _ago(s.last_health_check),
            "last_fleet_poll": _ago(s.last_fleet_poll),
        },
    }


@router.get("/fleet")
async def get_fleet(state: SharedPratyaksaState = Depends(_get_state)) -> dict:
    s = await state.read()
    return {
        "status": "success",
        "data": {
            "mode": s.mode.value,
            "fleet": [a.model_dump() for a in s.fleet_data],
            "total": len(s.fleet_data),
        },
    }


@router.get("/fleet/health")
async def get_fleet_health(state: SharedPratyaksaState = Depends(_get_state)) -> dict:
    s = await state.read()
    fleet = s.fleet_data
    normal = warning = critical = 0
    for asset in fleet:
        if asset.risk_level == "NORMAL":
            normal += 1
        elif asset.risk_level == "WARNING":
            warning += 1
        elif asset.risk_level == "CRITICAL":
            critical += 1
    avg_rul = 0.0
    if fleet:
        avg_rul = round(sum(a.lstm_rul_hours for a in fleet) / len(fleet) * 10.0) / 10.0

    return {
        "status": "success",
        "data": {
            "mode": s.mode.value,
            "total": len(fleet),
            "normal": normal,
            "warning": warning,
            "critical": critical,
            "avg_rul_hours": avg_rul,
        },
    }


async def _live_or_sim(
    state: SharedPratyaksaState,
    live: Callable[[], Awaitable[Any]],
    sim: Callable[[], Any],
) -> JSONResponse:
    s = await state.read()
    if s.mode == PratyaksaMode.LIVE and s.api_reachable:
        try:
            data = await live()
            return JSONResponse({"status": "success", "mode": "live", "data": data})
        except Exception as exc:
            return JSONResponse(
                status_code=502,
                content={
                    "status": "error",
                    "mode": "live",
                    "message": f"API Eksternal gagal: {exc}",
                    "hint": "Coba ganti ke mode SIMULASI jika ingin data simulasi.",
                },
            )
    return JSONResponse({"status": "success", "mode": "simulasi", "data": sim()})


@router.get("/result/{asset_id}")
async def get_result(
    asset_id: str,
    state: SharedPratyaksaState = Depends(_get_state),
    client: PratyaksaApiClient = Depends(_get_client),
) -> JSONResponse:
    return await _live_or_sim(
        state,
        lambda: client.get_result(asset_id),
        lambda: simulator.generate_result(asset_id),
    )


@router.post("/predict")
async def post_predict(
    body: PredictRequest,
    state: SharedPratyaksaState = Depends(_get_state),
    client: PratyaksaApiClient = Depends(_get_client),
) -> JSONResponse:
    if len(body.features) != 37:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": f"features[] harus berisi tepat 37 angka, tapi menerima {len(body.features)}",
                "expected": 37,
                "received": len(body.features),
            },
        )

    s = await state.read()
    if s.mode == PratyaksaMode.LIVE and s.api_reachable:
        try:
            data = await client.post_predict(body.model_dump())
            return JSONResponse({"status": "success", "mode": "live", "data": data})
        except Exception as exc:
            return JSONResponse(
                status_code=502,
                content={
                    "status": "error",
                    "mode": "live",
                    "message": f"Gagal hubungi API: {exc}",
                },
            )
    return JSONResponse(
        {"status": "success", "mode": "simulasi", "data": simulator.generate_predict(body).model_dump()}
    )


@router.post("/workorder")
async def post_workorder(
    component: str,
    risk_score: float,
    state: SharedPratyaksaState = Depends(_get_state),
    client: PratyaksaApiClient = Depends(_get_client),
) -> JSONResponse:
    allowed_components = ["brake", "hydraulic", "engine", "transmission"]
    if component not in allowed_components:
        raise BadRequestError(f"component harus: {allowed_components}")
    if not (0.0 <= risk_score <= 1.0):
        raise BadRequestError("risk_score harus 0.0 - 1.0")

    s = await state.read()
    if s.mode == PratyaksaMode.LIVE and s.api_reachable:
        try:
            data = await client.post_workorder(component, risk_score)
            return JSONResponse({"status": "success", "mode": "live", "data": data})
        except Exception as exc:
            return JSONResponse(
                status_code=502,
                content={"status": "error", "mode": "live", "message": f"Gagal hubungi API: {exc}"},
            )
    return JSONResponse(
        {
            "status": "success",
            "mode": "simulasi",
            "data": simulator.generate_workorder(component, risk_score).model_dump(),
        }
    )


@router.get("/features")
async def get_features(
    state: SharedPratyaksaState = Depends(_get_state),
    client: PratyaksaApiClient = Depends(_get_client),
) -> JSONResponse:
    return await _live_or_sim(state, client.get_features, simulator.generate_features)


@router.post("/reload-models")
async def post_reload_models(
    state: SharedPratyaksaState = Depends(_get_state),
    client: PratyaksaApiClient = Depends(_get_client),
) -> JSONResponse:
    return await _live_or_sim(
        state, client.post_reload_models, lambda: simulator.generate_reload_models().model_dump()
    )


@router.get("/explain/{prediction_id}")
async def get_explain(
    prediction_id: str,
    state: SharedPratyaksaState = Depends(_get_state),
    client: PratyaksaApiClient = Depends(_get_client),
) -> JSONResponse:
    return await _live_or_sim(
        state,
        lambda: client.get_explain(prediction_id),
        simulator.generate_explain,
    )


@router.post("/mode")
async def mode_switch(
    body: ModeSwitchRequest | None = None,
    state: SharedPratyaksaState = Depends(_get_state),
) -> JSONResponse:
    mode_val = body.mode if body else None

    if mode_val == "live":
        await state.update(manual_mode=PratyaksaMode.LIVE, mode=PratyaksaMode.LIVE)
        return JSONResponse(
            {
                "status": "success",
                "message": "Mode diatur ke LIVE. Semua data dari endpoint eksternal.",
                "data": {"mode": "live", "manual_mode": "live"},
            }
        )
    if mode_val == "simulasi":
        await state.update(
            manual_mode=PratyaksaMode.SIMULASI,
            mode=PratyaksaMode.SIMULASI,
            api_reachable=False,
            fleet_data=simulator.generate_fleet(),
        )
        return JSONResponse(
            {
                "status": "success",
                "message": "Mode diatur ke SIMULASI. Data dari simulator internal.",
                "data": {"mode": "simulasi", "manual_mode": "simulasi"},
            }
        )
    if mode_val is not None:
        raise BadRequestError(
            "mode harus 'live' atau 'simulasi', atau reset:true untuk auto-detect"
        )

    # reset → auto
    s = await state.update(manual_mode=None)
    return JSONResponse(
        {
            "status": "success",
            "message": "Mode di-reset ke AUTO.",
            "data": {"mode": s.mode.value, "manual_mode": None},
        }
    )


def _ago(ts: float | None) -> str | None:
    if ts is None:
        return None
    from datetime import datetime, timezone

    elapsed = int(datetime.now(timezone.utc).timestamp() - ts)
    return f"{elapsed}s ago"

"""Aggregate API router — mounts all v1 routes under ``/api/v1``."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    analisa,
    auth,
    dashboard,
    health_analytics,
    jenis_alat_berat,
    pratyaksa,
    svc,
    telemetry,
    unit_tambang,
    work_order,
)

api_router = APIRouter()


@api_router.get("/health")
async def health_check() -> dict:
    return {"status": "ok", "service": "Pratyaksa Backend", "version": "0.2.0"}


api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(jenis_alat_berat.router)
api_router.include_router(unit_tambang.router)
# health_analytics must be registered before analisa so /analisa/overview and
# /analisa/unit/{id} take precedence over /analisa/{id}.
api_router.include_router(health_analytics.router)
api_router.include_router(analisa.router)
api_router.include_router(telemetry.router)
api_router.include_router(work_order.router)
api_router.include_router(pratyaksa.router)
# Service routes (model upload / telegram alert) are available both at the API
# root (/svc/*) and under the v1 prefix (/api/v1/svc/*) so the frontend, whose
# only configurable base is PUBLIC_API_BASE, can reach them consistently.
api_router.include_router(svc.router)


def configure_v1() -> APIRouter:
    root = APIRouter(prefix="/api/v1")
    root.include_router(api_router)
    return root

"""Shared PRATYAKSA state and API client.

Mirrors ``backend_rust/src/pratyaksa/mod.rs`` — a shared, lockable state
containing cached fleet data, current mode, and reachability info, plus an
HTTP client for the external ML API.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import httpx

from app.core.config import AppConfig
from app.schemas.pratyaksa import FleetAsset, FleetResponse, HealthResponse


class PratyaksaMode(str, Enum):
    LIVE = "live"
    SIMULASI = "simulasi"


@dataclass
class PratyaksaState:
    mode: PratyaksaMode = PratyaksaMode.SIMULASI
    manual_mode: Optional[PratyaksaMode] = None
    fleet_data: list[FleetAsset] = field(default_factory=list)
    health_status: Optional[HealthResponse] = None
    last_health_check: Optional[float] = None
    last_fleet_poll: Optional[float] = None
    api_reachable: bool = False
    polling_active: bool = False
    predictions_stored: int = 0
    fleet_snapshots_stored: int = 0


class SharedPratyaksaState:
    """Async-safe wrapper around ``PratyaksaState``."""

    def __init__(self) -> None:
        self._state = PratyaksaState()
        self._lock = asyncio.Lock()

    async def read(self) -> PratyaksaState:
        async with self._lock:
            return self._state

    async def update(self, **kwargs: Any) -> PratyaksaState:
        async with self._lock:
            for key, value in kwargs.items():
                setattr(self._state, key, value)
            return self._state

    async def mutate(self, fn) -> Any:
        async with self._lock:
            return fn(self._state)


class PratyaksaApiClient:
    """HTTP client for the external PRATYAKSA ML API."""

    AUTH_HEADER = "X-API-Key"

    def __init__(self, config: AppConfig) -> None:
        self.base_url = config.pratyaksa_api_url.rstrip("/")
        self.api_key = config.pratyaksa_api_key
        self.client = httpx.AsyncClient(timeout=15.0)

    async def close(self) -> None:
        await self.client.aclose()

    def _headers(self) -> dict[str, str]:
        return {self.AUTH_HEADER: self.api_key}

    async def check_health(self) -> HealthResponse:
        url = f"{self.base_url}/health"
        resp = await self.client.get(url, timeout=5.0)
        resp.raise_for_status()
        return HealthResponse(**resp.json())

    async def get_fleet(self) -> FleetResponse:
        url = f"{self.base_url}/fleet"
        resp = await self.client.get(url, headers=self._headers(), timeout=10.0)
        if resp.status_code == 401:
            raise RuntimeError("Unauthorized: API Key salah atau tidak dikirim")
        resp.raise_for_status()
        return FleetResponse(**resp.json())

    async def get_result(self, asset_id: str) -> dict[str, Any]:
        url = f"{self.base_url}/result/{asset_id}"
        resp = await self.client.get(url, headers=self._headers(), timeout=10.0)
        resp.raise_for_status()
        return resp.json()

    async def get_features(self) -> dict[str, Any]:
        url = f"{self.base_url}/features"
        resp = await self.client.get(url, headers=self._headers(), timeout=10.0)
        resp.raise_for_status()
        return resp.json()

    async def get_explain(self, prediction_id: str) -> dict[str, Any]:
        url = f"{self.base_url}/explain/{prediction_id}"
        resp = await self.client.get(url, headers=self._headers(), timeout=10.0)
        resp.raise_for_status()
        return resp.json()

    async def post_reload_models(self) -> dict[str, Any]:
        url = f"{self.base_url}/reload-models"
        resp = await self.client.post(url, headers=self._headers(), timeout=30.0)
        resp.raise_for_status()
        return resp.json()

    async def post_predict(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/predict"
        resp = await self.client.post(url, headers=self._headers(), json=payload)
        resp.raise_for_status()
        return resp.json()

    async def post_workorder(self, component: str, risk_score: float) -> dict[str, Any]:
        url = f"{self.base_url}/workorder?component={component}&risk_score={risk_score}"
        resp = await self.client.post(url, headers=self._headers())
        resp.raise_for_status()
        return resp.json()


def now_epoch() -> float:
    return time.time()

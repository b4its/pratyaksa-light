"""Shared PRATYAKSA state.

Pratyaksa runs in **simulation-only** mode: all fleet/prediction data comes
from the internal deterministic simulator (``app.pratyaksa.simulator``).  There
is no external ML API client — the previous HTTP polling/sync machinery has
been removed so the stack never talks to any live endpoint.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from app.schemas.pratyaksa import FleetAsset, HealthResponse


class PratyaksaMode(str, Enum):
    SIMULASI = "simulasi"


@dataclass
class PratyaksaState:
    mode: PratyaksaMode = PratyaksaMode.SIMULASI
    fleet_data: list[FleetAsset] = field(default_factory=list)
    health_status: Optional[HealthResponse] = None
    generated_at: Optional[float] = None


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


def now_epoch() -> float:
    return time.time()

"""MongoDB access layer with batched, non-blocking writes.

Mirrors the Rust ``MongoDb`` batch-consumer design: producers enqueue documents
into in-memory queues and background tasks flush them via ``insert_many`` when a
batch fills up or a flush interval elapses.

Uses the async PyMongo API (``AsyncMongoClient``), the successor to the now
deprecated ``motor`` driver.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

logger = logging.getLogger("pratyaksa.db.mongo")


class _BatchQueue:
    """A tiny async queue that flushes to a collection in bulk."""

    def __init__(
        self,
        collection: Any,
        name: str,
        max_batch: int,
        interval_ms: int,
    ) -> None:
        self.collection = collection
        self.name = name
        self.max_batch = max_batch
        self.interval = interval_ms / 1000.0
        self._queue: asyncio.Queue[dict] = asyncio.Queue()
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self._flush_locked(self._drain())

    def enqueue(self, doc: dict) -> None:
        self._queue.put_nowait(doc)

    def _drain(self) -> list[dict]:
        items: list[dict] = []
        while not self._queue.empty():
            try:
                items.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:  # pragma: no cover
                break
        return items

    async def _flush_locked(self, items: list[dict]) -> None:
        if not items:
            return
        try:
            await self.collection.insert_many(items)
            logger.debug("MongoDB batch inserted %d %s records", len(items), self.name)
        except Exception as exc:  # pragma: no cover - network dependent
            logger.error("MongoDB batch insert failed for %s: %s", self.name, exc)

    async def _run(self) -> None:
        batch: list[dict] = []
        while True:
            try:
                item = await asyncio.wait_for(self._queue.get(), timeout=self.interval)
                batch.append(item)
                if len(batch) >= self.max_batch:
                    await self._flush_locked(batch)
                    batch = []
            except asyncio.TimeoutError:
                if batch:
                    await self._flush_locked(batch)
                    batch = []


class MongoDb:
    def __init__(self, client: AsyncMongoClient, database: AsyncDatabase, batch_size: int) -> None:
        self.client = client
        self.db = database
        self.batch_size = batch_size
        self._queues: dict[str, _BatchQueue] = {}

        specs = {
            "live_predictions": (batch_size, 500),
            "live_fleet_snapshots": (batch_size, 1000),
            "live_sensor_readings": (batch_size, 500),
            "live_drift_logs": (max(50, batch_size // 2), 2000),
            "live_work_orders": (max(50, batch_size // 2), 2000),
        }
        for name, (max_batch, interval_ms) in specs.items():
            self._queues[name] = _BatchQueue(
                self.db[name], name, max_batch, interval_ms
            )

    @classmethod
    async def connect(
        cls, mongodb_url: str, db_name: str, batch_size: int = 100
    ) -> "MongoDb":
        client: AsyncMongoClient = AsyncMongoClient(mongodb_url, serverSelectionTimeoutMS=5000)
        await client.admin.command("ping")
        db = client[db_name]
        instance = cls(client, db, batch_size)  # type: ignore[arg-type]
        return instance

    def start_consumers(self) -> None:
        for queue in self._queues.values():
            queue.start()
        logger.info("MongoDB batch consumers spawned for live API data")

    async def close(self) -> None:
        for queue in self._queues.values():
            await queue.stop()
        await self.client.close()

    # ------------------------------------------------------------------
    # Collection access (direct read queries)
    # ------------------------------------------------------------------
    def collection(self, name: str):
        return self.db[name]

    # ------------------------------------------------------------------
    # High-speed producers (non-blocking via queue)
    # ------------------------------------------------------------------
    def store_prediction(self, doc: dict) -> None:
        self._queues["live_predictions"].enqueue(doc)

    def store_fleet_snapshot(self, doc: dict) -> None:
        self._queues["live_fleet_snapshots"].enqueue(doc)

    def store_sensor_reading(self, doc: dict) -> None:
        self._queues["live_sensor_readings"].enqueue(doc)

    def store_drift_log(self, doc: dict) -> None:
        self._queues["live_drift_logs"].enqueue(doc)

    def store_work_order(self, doc: dict) -> None:
        self._queues["live_work_orders"].enqueue(doc)

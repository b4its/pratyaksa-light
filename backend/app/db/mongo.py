"""MongoDB access layer using the async PyMongo API.

The live-API batch consumers (predictions / fleet snapshots / drift logs) were
removed together with the external ML integration. MongoDB is now used only for
the flexible-schema ``analisa_kerusakan`` collection, accessed directly via
``MongoDb.collection(name)``.
"""

from __future__ import annotations

import logging

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

logger = logging.getLogger("pratyaksa.db.mongo")


class MongoDb:
    def __init__(self, client: AsyncMongoClient, database: AsyncDatabase) -> None:
        self.client = client
        self.db = database

    @classmethod
    async def connect(cls, mongodb_url: str, db_name: str) -> "MongoDb":
        client: AsyncMongoClient = AsyncMongoClient(mongodb_url, serverSelectionTimeoutMS=5000)
        await client.admin.command("ping")
        db = client[db_name]
        return cls(client, db)  # type: ignore[arg-type]

    def start_consumers(self) -> None:
        # Retained as a no-op for lifespan compatibility.
        logger.info("MongoDB connected (direct access, no batch consumers)")

    async def close(self) -> None:
        await self.client.close()

    # ------------------------------------------------------------------
    # Collection access (direct read/write queries)
    # ------------------------------------------------------------------
    def collection(self, name: str):
        return self.db[name]

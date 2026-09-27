"""PostgreSQL access layer (asyncpg pool).

Mirrors the Rust ``PostgresDb`` — a connection pool plus migration runner.
"""

from __future__ import annotations

import logging
from pathlib import Path

import asyncpg

logger = logging.getLogger("pratyaksa.db.postgres")

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


class PostgresDb:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    @classmethod
    async def connect(cls, database_url: str, min_size: int = 2, max_size: int = 20) -> "PostgresDb":
        pool = await asyncpg.create_pool(
            dsn=database_url,
            min_size=min_size,
            max_size=max_size,
            command_timeout=30,
        )
        return cls(pool)  # type: ignore[arg-type]

    async def close(self) -> None:
        await self.pool.close()

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------
    async def fetch(self, query: str, *args) -> list[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args) -> asyncpg.Record | None:
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def execute(self, query: str, *args) -> str:
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    # ------------------------------------------------------------------
    # Migrations
    # ------------------------------------------------------------------
    async def run_migrations(self) -> None:
        """Apply every ``*.sql`` file in the migrations directory in order.

        A lightweight ``schema_migrations`` table tracks applied files so the
        runner is idempotent (equivalent to sqlx::migrate!).
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            applied = {
                row["version"]
                for row in await conn.fetch("SELECT version FROM schema_migrations")
            }

        files = sorted(MIGRATIONS_DIR.glob("*.sql"))
        for path in files:
            version = path.name
            if version in applied:
                continue
            sql = path.read_text(encoding="utf-8")
            logger.info("Applying migration %s", version)
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(sql)
                    await conn.execute(
                        "INSERT INTO schema_migrations (version) VALUES ($1)", version
                    )

"""Pytest fixtures.

Integration tests connect to a local PostgreSQL/MongoDB (the same containers
used by the original project).  When unavailable, the DB-backed tests are
skipped and only pure unit tests run.
"""

from __future__ import annotations

import asyncio
import os

import pytest
import pytest_asyncio

os.environ.setdefault("DATABASE_URL", "postgresql://pratyaksa:pratyaksa_secret@localhost:5466/pratyaksa_db")
os.environ.setdefault("MONGODB_URL", "mongodb://pratyaksa:pratyaksa_secret@localhost:27051")
os.environ.setdefault("MONGODB_NAME", "pratyaksa")
os.environ.setdefault("JWT_SECRET", "test_secret")
os.environ.setdefault("MONGO_REQUIRED", "false")
os.environ.setdefault("PRATYAKSA_POLL_INTERVAL", "3600")
os.environ.setdefault("ML_SYNC_INTERVAL", "3600")


async def _pg_available() -> bool:
    try:
        import asyncpg

        conn = await asyncpg.connect(os.environ["DATABASE_URL"], timeout=3)
        await conn.close()
        return True
    except Exception:
        return False


async def _mongo_available() -> bool:
    try:
        from pymongo import AsyncMongoClient

        client: AsyncMongoClient = AsyncMongoClient(os.environ["MONGODB_URL"], serverSelectionTimeoutMS=3000)
        await client.admin.command("ping")
        await client.close()
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def pg_available() -> bool:
    return asyncio.get_event_loop().run_until_complete(_pg_available())


@pytest.fixture(scope="session")
def mongo_available() -> bool:
    return asyncio.get_event_loop().run_until_complete(_mongo_available())


@pytest_asyncio.fixture
async def client():
    import httpx

    from app.main import create_app

    app = create_app()
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

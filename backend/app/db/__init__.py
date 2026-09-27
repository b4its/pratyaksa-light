"""Database singletons + lifecycle helpers."""

from __future__ import annotations

from app.db.mongo import MongoDb
from app.db.postgres import PostgresDb

__all__ = ["MongoDb", "PostgresDb"]

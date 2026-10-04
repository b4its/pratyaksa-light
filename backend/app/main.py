"""Pratyaksa FastAPI application factory."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import configure_v1
from app.api.routes import svc as svc_routes
from app.core.config import AppConfig, get_config
from app.core.errors import (
    AppError,
    app_error_handler,
    generic_exception_handler,
    http_exception_handler,
    integrity_exception_handler,
    validation_exception_handler,
)
from app.db.mongo import MongoDb
from app.db.postgres import PostgresDb
from app.pratyaksa import SharedPratyaksaState
from app.pratyaksa.simulator import generate_fleet, generate_health
from app.pratyaksa.state import now_epoch

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pratyaksa")


@asynccontextmanager
async def lifespan(app: FastAPI):
    config: AppConfig = app.state.config
    logger.info("🚀 Starting Pratyaksa Backend v0.2.0 (FastAPI)")

    # --- PostgreSQL ---
    if config.database_url:
        logger.info("📦 Connecting to PostgreSQL...")
        pg = await PostgresDb.connect(config.database_url)
        await pg.run_migrations()
        app.state.pg = pg
        logger.info("✅ PostgreSQL connected and migrations applied")
    else:
        logger.warning("⚠️  DATABASE_URL not set — PostgreSQL endpoints will fail")
        app.state.pg = None

    # --- MongoDB ---
    if config.mongodb_url:
        logger.info("📦 Connecting to MongoDB...")
        try:
            mongo = await MongoDb.connect(config.mongodb_url, config.mongodb_name)
            mongo.start_consumers()
            app.state.mongo = mongo
            logger.info("✅ MongoDB connected")
        except Exception as exc:
            if config.mongo_db_required:
                raise
            logger.warning("⚠️  MongoDB unavailable: %s", exc)
            app.state.mongo = None
    else:
        logger.warning("⚠️  MONGODB_URL not set — Mongo endpoints will fail")
        app.state.mongo = None

    # --- PRATYAKSA shared state (simulation-only) ---
    app.state.pratyaksa = SharedPratyaksaState()
    await app.state.pratyaksa.update(
        fleet_data=generate_fleet(),
        health_status=generate_health(),
        generated_at=now_epoch(),
    )
    logger.info("🧪 Pratyaksa running in SIMULATION mode (no external API)")

    try:
        yield
    finally:
        if app.state.mongo is not None:
            await app.state.mongo.close()
        if app.state.pg is not None:
            await app.state.pg.close()
        logger.info("🛑 Shutdown complete")


def create_app() -> FastAPI:
    config = get_config()
    app = FastAPI(
        title="Pratyaksa Backend",
        version="0.2.0",
        description="Mining intelligence platform — FastAPI port of the Rust backend.",
        lifespan=lifespan,
    )
    app.state.config = config

    origins = config.cors_origins or ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
        max_age=3600,
    )

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # Map raw asyncpg integrity violations (unique/FK) to clean 4xx responses
    # so driver messages never leak as 500s.
    try:
        from asyncpg.exceptions import ForeignKeyViolationError, UniqueViolationError

        app.add_exception_handler(UniqueViolationError, integrity_exception_handler)
        app.add_exception_handler(ForeignKeyViolationError, integrity_exception_handler)
    except Exception:  # pragma: no cover - asyncpg always present in prod
        pass

    app.include_router(configure_v1())
    app.include_router(svc_routes.router)

    # Serve uploaded 3D models. ``/svc/upload-model`` writes to
    # ``config.media_dir`` (…/media/models) and returns ``/media/models/<file>``,
    # so we mount the media *root* (parent of the models dir) at ``/media``.
    models_dir = Path(config.media_dir)
    media_root = models_dir.parent
    media_root.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=str(media_root)), name="media")

    return app


app = create_app()

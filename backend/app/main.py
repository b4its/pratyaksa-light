"""Pratyaksa FastAPI application factory."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import configure_v1
from app.api.routes import svc as svc_routes
from app.core.config import AppConfig, get_config
from app.core.errors import (
    AppError,
    app_error_handler,
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.db.mongo import MongoDb
from app.db.postgres import PostgresDb
from app.pratyaksa import PratyaksaApiClient, SharedPratyaksaState
from app.pratyaksa.polling import start_polling
from app.pratyaksa.sync import start_sync

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
            mongo = await MongoDb.connect(
                config.mongodb_url, config.mongodb_name, config.mongo_batch_size
            )
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

    # --- PRATYAKSA shared state + client ---
    app.state.pratyaksa = SharedPratyaksaState()
    app.state.pratyaksa_client = PratyaksaApiClient(config)

    # --- Background tasks ---
    tasks: list[asyncio.Task] = []
    if app.state.mongo is not None:
        tasks.append(
            asyncio.create_task(
                start_polling(
                    app.state.pratyaksa,
                    app.state.pratyaksa_client,
                    config.pratyaksa_poll_interval_secs,
                    app.state.mongo,
                )
            )
        )
        tasks.append(
            asyncio.create_task(
                start_sync(app.state.pratyaksa, config, app.state.mongo)
            )
        )
        logger.info("🔁 Background polling & sync tasks started")

    try:
        yield
    finally:
        for task in tasks:
            task.cancel()
        for task in tasks:
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        if app.state.mongo is not None:
            await app.state.mongo.close()
        if app.state.pg is not None:
            await app.state.pg.close()
        await app.state.pratyaksa_client.close()
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

    app.include_router(configure_v1())
    app.include_router(svc_routes.router)

    return app


app = create_app()

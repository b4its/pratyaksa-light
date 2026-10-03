"""Application configuration.

Loads settings from environment variables.  Pratyaksa is simulation-only: the
external ML API / ML-PostgreSQL sync settings have been removed so the backend
never connects to any live endpoint.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache

try:  # optional .env loading
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv always present in prod requirements
    pass


def _env(key: str, default: str | None = None) -> str | None:
    value = os.environ.get(key)
    if value is None or value == "":
        return default
    return value


@dataclass
class AppConfig:
    server_host: str = "0.0.0.0"
    server_port: int = 8080
    database_url: str = ""
    mongodb_url: str = ""
    mongodb_name: str = "pratyaksa"
    jwt_secret: str = "super_secret_pratyaksa_key_2024"
    jwt_expiry_hours: int = 24
    mongo_db_required: bool = True
    telegram_grpc_target: str = "telegram-bot:50051"
    media_dir: str = "./media/models"
    cors_origins: list[str] = field(default_factory=lambda: ["*"])

    @classmethod
    def from_env(cls) -> "AppConfig":
        cors_raw = _env("CORS_ORIGINS", "*") or "*"
        origins = [o.strip() for o in cors_raw.split(",") if o.strip()]

        return cls(
            server_host=_env("SERVER_HOST", "0.0.0.0") or "0.0.0.0",
            server_port=int(_env("SERVER_PORT", "8080") or "8080"),
            database_url=_env("DATABASE_URL", "") or "",
            mongodb_url=_env("MONGODB_URL", "") or "",
            mongodb_name=_env("MONGODB_NAME", "pratyaksa") or "pratyaksa",
            jwt_secret=_env("JWT_SECRET", "super_secret_pratyaksa_key_2024")
            or "super_secret_pratyaksa_key_2024",
            jwt_expiry_hours=int(_env("JWT_EXPIRY_HOURS", "24") or "24"),
            mongo_db_required=(_env("MONGO_REQUIRED", "true") or "true").lower()
            not in ("0", "false", "no"),
            telegram_grpc_target=_env("TELEGRAM_GRPC_TARGET", "telegram-bot:50051")
            or "telegram-bot:50051",
            media_dir=_env("MEDIA_DIR", "./media/models") or "./media/models",
            cors_origins=origins,
        )


@lru_cache
def get_config() -> AppConfig:
    return AppConfig.from_env()

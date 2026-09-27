"""Application configuration.

Loads settings from environment variables, mirroring the original Rust
``AppConfig`` (see ``backend_rust/src/config.rs``).
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
    live_api_url: str = "http://192.168.101.3:6000"
    live_api_key: str = "dev-key-pratyaksa"
    pratyaksa_api_url: str = "http://192.168.101.3:6000"
    pratyaksa_api_key: str = "dev-key-pratyaksa"
    pratyaksa_poll_interval_secs: int = 5
    custom_api_url: str = "http://192.168.101.3:7000"
    ml_postgres_url: str = (
        "postgresql://pratyaksa:pratyaksa_secret@192.168.101.3:5432/pratyaksa"
    )
    ml_sync_interval_secs: int = 60
    mongo_batch_size: int = 100
    mongo_db_required: bool = True
    cors_origins: list[str] = field(default_factory=lambda: ["*"])

    @classmethod
    def from_env(cls) -> "AppConfig":
        live_api_url = _env("LIVE_API_URL") or _env("PRATYAKSA_API_URL") or "http://192.168.101.3:6000"
        live_api_key = _env("LIVE_API_KEY") or _env("PRATYAKSA_API_KEY") or "dev-key-pratyaksa"

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
            live_api_url=live_api_url,
            live_api_key=live_api_key,
            pratyaksa_api_url=live_api_url,
            pratyaksa_api_key=live_api_key,
            pratyaksa_poll_interval_secs=int(_env("PRATYAKSA_POLL_INTERVAL", "5") or "5"),
            custom_api_url=_env("CUSTOM_API_URL", "http://192.168.101.3:7000")
            or "http://192.168.101.3:7000",
            ml_postgres_url=_env(
                "ML_POSTGRES_URL",
                "postgresql://pratyaksa:pratyaksa_secret@192.168.101.3:5432/pratyaksa",
            )
            or "postgresql://pratyaksa:pratyaksa_secret@192.168.101.3:5432/pratyaksa",
            ml_sync_interval_secs=int(_env("ML_SYNC_INTERVAL", "60") or "60"),
            mongo_batch_size=int(_env("MONGO_BATCH_SIZE", "100") or "100"),
            mongo_db_required=(_env("MONGO_REQUIRED", "true") or "true").lower()
            not in ("0", "false", "no"),
            cors_origins=origins,
        )


@lru_cache
def get_config() -> AppConfig:
    return AppConfig.from_env()

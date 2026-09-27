"""Telegram bot configuration from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover
    pass


def _env(key: str, default: str = "") -> str:
    value = os.environ.get(key)
    return default if value is None or value == "" else value


@dataclass
class BotConfig:
    grpc_host: str
    grpc_port: int
    bot_token: str
    default_chat_id: int | None
    backend_url: str
    wo_link_base: str
    subscribers_file: str

    @classmethod
    def from_env(cls) -> "BotConfig":
        chat_raw = _env("TELEGRAM_CHAT_ID").strip()
        chat_id: int | None = None
        if chat_raw:
            try:
                chat_id = int(chat_raw)
            except ValueError:
                chat_id = None

        return cls(
            grpc_host=_env("GRPC_HOST", "0.0.0.0"),
            grpc_port=int(_env("GRPC_PORT", "50051")),
            bot_token=_env("TELEGRAM_BOT_TOKEN"),
            default_chat_id=chat_id,
            backend_url=_env("BACKEND_URL", "http://backend:8080"),
            wo_link_base=_env("WO_LINK_BASE", "http://localhost"),
            subscribers_file=_env("SUBSCRIBERS_FILE", "/app/data/subscribers.json"),
        )


@lru_cache
def get_config() -> BotConfig:
    return BotConfig.from_env()

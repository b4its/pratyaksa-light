"""Shared bot state: subscribers, fleet cache, Telegram + backend clients."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

import httpx

from . import messages as msg
from .config import BotConfig

logger = logging.getLogger("pratyaksa.bot")


class BotState:
    def __init__(self, config: BotConfig) -> None:
        self.config = config
        self.bot_token = config.bot_token
        self.http = httpx.AsyncClient(timeout=20.0)
        self.subscribers: set[int] = set()
        self.fleet: dict[str, dict[str, str]] = {}
        self._lock = asyncio.Lock()
        self._load_subscribers()
        if config.default_chat_id is not None:
            self.subscribers.add(config.default_chat_id)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _load_subscribers(self) -> None:
        path = self.config.subscribers_file
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, list):
                self.subscribers.update(int(x) for x in data)
        except (FileNotFoundError, ValueError, TypeError):
            pass

    async def persist_subscribers(self) -> None:
        path = self.config.subscribers_file
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(sorted(self.subscribers), fh)
        except OSError as exc:  # pragma: no cover
            logger.warning("Gagal menyimpan subscribers: %s", exc)

    # ------------------------------------------------------------------
    # Subscriber management
    # ------------------------------------------------------------------
    async def add_subscriber(self, chat_id: int) -> bool:
        async with self._lock:
            is_new = chat_id not in self.subscribers
            self.subscribers.add(chat_id)
        if is_new:
            await self.persist_subscribers()
        return is_new

    async def remove_subscriber(self, chat_id: int) -> bool:
        async with self._lock:
            existed = chat_id in self.subscribers
            self.subscribers.discard(chat_id)
        if existed:
            await self.persist_subscribers()
        return existed

    def subscriber_list(self) -> list[int]:
        return list(self.subscribers)

    # ------------------------------------------------------------------
    # Telegram API
    # ------------------------------------------------------------------
    async def send_message(self, chat_id: int, text: str) -> None:
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        resp = await self.http.post(
            url,
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"Telegram API error {resp.status_code}: {resp.text}")

    async def send_message_with_keyboard(
        self, chat_id: int, text: str, keyboard: list[list[dict[str, str]]]
    ) -> None:
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        resp = await self.http.post(
            url,
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
                "reply_markup": {"inline_keyboard": keyboard},
            },
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"Telegram API error {resp.status_code}: {resp.text}")

    # ------------------------------------------------------------------
    # Backend fetchers
    # ------------------------------------------------------------------
    def _backend(self, path: str) -> str:
        return f"{self.config.backend_url.rstrip('/')}{path}"

    async def _get_json(self, path: str) -> dict[str, Any]:
        resp = await self.http.get(self._backend(path))
        if resp.status_code >= 400:
            raise RuntimeError(f"backend membalas HTTP {resp.status_code}")
        return resp.json()

    async def fetch_fleet_summary(self) -> str:
        v = await self._get_json("/api/v1/fleet-summary")
        return msg.build_fleet_summary(v.get("data", {}))

    async def fetch_pratyaksa_status(self) -> str:
        v = await self._get_json("/api/v1/pratyaksa/status")
        return msg.build_pratyaksa_status(v.get("data", {}))

    async def fetch_unit_detail(self, asset_id: str) -> str:
        v = await self._get_json(f"/api/v1/pratyaksa/result/{asset_id}")
        if v.get("status") == "error":
            raise RuntimeError(v.get("message", "Error tidak diketahui"))
        return msg.build_unit_detail(v.get("mode", "simulasi"), v.get("data", {}))

    async def fetch_detail_report(self) -> str:
        fleet_summary = await self.fetch_fleet_summary()
        fleet_v = await self._get_json("/api/v1/pratyaksa/fleet")
        fleet = fleet_v.get("data", {}).get("fleet", []) or []
        mode = fleet_v.get("data", {}).get("mode", "simulasi")

        health_v = await self._get_json("/api/v1/pratyaksa/fleet/health")
        avg_rul = float(health_v.get("data", {}).get("avg_rul_hours", 0.0) or 0.0)

        return msg.build_detail_report(fleet_summary, mode, avg_rul, fleet)

    async def close(self) -> None:
        await self.http.aclose()

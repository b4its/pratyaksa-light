"""Telegram long-polling loop (getUpdates) handling commands + callbacks."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from . import messages as msg
from .state import BotState

logger = logging.getLogger("pratyaksa.bot.polling")


async def _answer_callback(state: BotState, cb_id: str) -> None:
    if not cb_id:
        return
    url = f"https://api.telegram.org/bot{state.bot_token}/answerCallbackQuery"
    try:
        await state.http.post(url, json={"callback_query_id": cb_id})
    except Exception as exc:  # pragma: no cover
        logger.warning("answerCallbackQuery gagal: %s", exc)


async def _handle_callback(state: BotState, cq: dict[str, Any]) -> None:
    chat_id = (cq.get("message") or {}).get("chat", {}).get("id")
    data = cq.get("data", "")
    await _answer_callback(state, cq.get("id", ""))
    if chat_id is None:
        return
    chat_id = int(chat_id)

    if data != "/down":
        await state.add_subscriber(chat_id)

    try:
        if data == "/status":
            reply = await state.fetch_fleet_summary()
        elif data == "/detail":
            reply = await state.fetch_detail_report()
        elif data == "/pratyaksa":
            reply = await state.fetch_pratyaksa_status()
        elif data == "/down":
            existed = await state.remove_subscriber(chat_id)
            reply = _down_message(existed)
        else:
            reply = "Perintah tidak dikenal"
    except Exception as exc:
        reply = f"⚠️ {exc}"

    try:
        await state.send_message(chat_id, reply)
    except Exception as exc:  # pragma: no cover
        logger.warning("Gagal kirim callback response ke %s: %s", chat_id, exc)


def _down_message(existed: bool) -> str:
    if existed:
        return (
            "⛔ <b>Berhenti Berlangganan</b>\n\n"
            "Anda telah berhenti menerima notifikasi dari PRATYAKSA.\n\n"
            "Untuk mulai menerima notifikasi lagi, ketik /start kapan saja.\n\n"
            "Terima kasih telah menggunakan PRATYAKSA."
        )
    return (
        "ℹ️ Anda saat ini tidak menerima notifikasi dari PRATYAKSA.\n\n"
        "Untuk mulai menerima notifikasi, ketik /start."
    )


async def _handle_command(state: BotState, chat_id: int, cmd: str, text: str) -> None:
    try:
        if cmd == "/start":
            is_new = await state.add_subscriber(chat_id)
            await state.send_message_with_keyboard(
                chat_id, msg.greeting_message(), msg.start_menu_keyboard()
            )
            if is_new:
                logger.info("Subscriber baru terdaftar: %s", chat_id)
        elif cmd == "/status":
            await state.add_subscriber(chat_id)
            try:
                reply = await state.fetch_fleet_summary()
            except Exception as exc:
                reply = f"⚠️ Gagal mengambil status fleet: {exc}.\nCoba lagi sebentar."
            await state.send_message(chat_id, reply)
        elif cmd == "/detail":
            await state.add_subscriber(chat_id)
            try:
                reply = await state.fetch_detail_report()
            except Exception as exc:
                reply = f"⚠️ Gagal mengambil detail laporan: {exc}.\nCoba lagi sebentar."
            await state.send_message(chat_id, reply)
        elif cmd in ("/pratyaksa", "/ds"):
            await state.add_subscriber(chat_id)
            try:
                reply = await state.fetch_pratyaksa_status()
            except Exception as exc:
                reply = f"⚠️ Gagal mengambil status Pratyaksa: {exc}.\nCoba lagi sebentar."
            await state.send_message(chat_id, reply)
        elif cmd == "/unit":
            await state.add_subscriber(chat_id)
            parts = text.split()
            if len(parts) < 2:
                help_msg = (
                    "ℹ️ <b>Cara pakai:</b>\n\n"
                    "/unit &lt;asset_id&gt;\n\n"
                    "<b>Contoh:</b>\n"
                    "/unit WA600-001\n"
                    "/unit HD785-001\n"
                    "/unit DT-001"
                )
                await state.send_message(chat_id, help_msg)
            else:
                asset_id = parts[1]
                try:
                    reply = await state.fetch_unit_detail(asset_id)
                except Exception as exc:
                    reply = (
                        f"⚠️ Gagal mengambil detail unit <b>{asset_id}</b>: {exc}.\n\n"
                        "Pastikan asset_id valid dan tersedia di fleet."
                    )
                await state.send_message(chat_id, reply)
        elif cmd == "/menu":
            await state.send_message_with_keyboard(
                chat_id,
                "📋 <b>Menu PRATYAKSA</b>\n\nSilakan pilih jenis laporan:",
                msg.start_menu_keyboard(),
            )
        elif cmd in ("/down", "/berhenti", "/stop"):
            existed = await state.remove_subscriber(chat_id)
            await state.send_message(chat_id, _down_message(existed))
        else:
            await state.send_message_with_keyboard(
                chat_id,
                "Perintah tidak dikenal. Gunakan /start untuk menu, atau pilih salah satu di bawah ini:",
                msg.start_menu_keyboard(),
            )
    except Exception as exc:  # pragma: no cover
        logger.warning("Gagal memproses %s untuk %s: %s", cmd, chat_id, exc)


async def run_polling(state: BotState) -> None:
    if not state.bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN kosong — polling command dinonaktifkan")
        return

    url = f"https://api.telegram.org/bot{state.bot_token}/getUpdates"
    offset = 0
    logger.info("Telegram polling aktif (getUpdates)")

    while True:
        try:
            resp = await state.http.get(
                url,
                params={
                    "timeout": 30,
                    "offset": offset,
                    "allowed_updates": '["message","callback_query"]',
                },
                timeout=40.0,
            )
            body = resp.json()
        except Exception as exc:
            logger.warning("getUpdates error: %s", exc)
            await asyncio.sleep(3)
            continue

        updates = body.get("result")
        if not isinstance(updates, list):
            await asyncio.sleep(2)
            continue

        for upd in updates:
            uid = upd.get("update_id")
            if isinstance(uid, int):
                offset = max(offset, uid + 1)

            if "callback_query" in upd:
                asyncio.create_task(_handle_callback(state, upd["callback_query"]))
                continue

            message = upd.get("message") or {}
            chat = message.get("chat") or {}
            chat_id = chat.get("id")
            text = (message.get("text") or "").strip()
            if chat_id is None or not text:
                continue

            cmd = text.split()[0].split("@")[0].lower()
            asyncio.create_task(_handle_command(state, int(chat_id), cmd, text))

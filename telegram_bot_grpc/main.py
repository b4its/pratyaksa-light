"""Telegram bot service entrypoint: gRPC server + Telegram polling loop."""

from __future__ import annotations

import asyncio
import logging
import signal

from bot.config import get_config
from bot.grpc_server import serve
from bot.polling import run_polling
from bot.state import BotState

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pratyaksa.bot")


async def main() -> None:
    config = get_config()
    state = BotState(config)
    await state.persist_subscribers()

    logger.info("Memuat %d subscriber awal", len(state.subscribers))
    if not config.bot_token:
        logger.warning(
            "TELEGRAM_BOT_TOKEN belum diset — bot tidak akan mengirim/menerima pesan"
        )

    server = await serve(state, config.grpc_host, config.grpc_port)
    polling_task = asyncio.create_task(run_polling(state))

    stop = asyncio.Event()

    def _shutdown(*_: object) -> None:
        logger.info("Shutdown signal diterima, menutup server...")
        stop.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _shutdown)
        except NotImplementedError:  # pragma: no cover - Windows
            pass

    try:
        await stop.wait()
    finally:
        polling_task.cancel()
        await server.stop(grace=3)
        await state.close()


if __name__ == "__main__":
    asyncio.run(main())

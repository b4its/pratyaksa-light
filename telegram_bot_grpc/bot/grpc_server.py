"""gRPC AlertService implementation."""

from __future__ import annotations

import logging
from concurrent import futures
from typing import Any

import grpc

from . import messages as msg
from .proto_loader import ensure_stubs
from .state import BotState

logger = logging.getLogger("pratyaksa.bot.grpc")

alert_pb2, alert_pb2_grpc = ensure_stubs()


class AlertService(alert_pb2_grpc.AlertServiceServicer):
    def __init__(self, state: BotState) -> None:
        self.state = state

    async def SendAlert(self, request, context):  # noqa: N802 (proto name)
        d: dict[str, str] = {
            "asset_id": request.asset_id,
            "model": request.model,
            "lokasi": request.lokasi,
            "status": request.status,
            "rul": request.rul,
            "shap1": request.shap1,
            "shap2": request.shap2,
            "part_name": request.part_name,
            "part_no": request.part_no,
            "stok": request.stok,
        }

        if not self.state.bot_token:
            await context.abort(
                grpc.StatusCode.FAILED_PRECONDITION,
                "TELEGRAM_BOT_TOKEN belum dikonfigurasi pada service",
            )

        self.state.fleet[d["asset_id"]] = {
            "risk_level": d["status"],
            "last_update": d["lokasi"],
        }

        targets = self.state.subscriber_list()
        if not targets:
            await context.abort(
                grpc.StatusCode.FAILED_PRECONDITION,
                "Belum ada subscriber. Minta user menjalankan /start ke bot.",
            )

        message = msg.build_alert_message(d, self.state.config.wo_link_base)
        delivered = 0
        last_err: str | None = None
        for chat_id in targets:
            try:
                await self.state.send_message(chat_id, message)
                delivered += 1
            except Exception as exc:  # pragma: no cover - network
                logger.warning("Gagal kirim alert %s ke %s: %s", d["asset_id"], chat_id, exc)
                last_err = str(exc)

        if delivered == 0:
            await context.abort(
                grpc.StatusCode.UNAVAILABLE,
                last_err or "Gagal mengirim ke semua subscriber",
            )

        logger.info(
            "Alert %s terkirim ke %d/%d subscriber", d["asset_id"], delivered, len(targets)
        )
        return alert_pb2.AlertResponse(
            success=True,
            message=f"Alert terkirim ke {delivered}/{len(targets)} device",
            asset_id=d["asset_id"],
        )

    async def HealthCheck(self, request, context):  # noqa: N802
        total = len(self.state.fleet)
        critical = sum(
            1 for v in self.state.fleet.values() if v.get("risk_level", "").upper() == "CRITICAL"
        )
        return alert_pb2.HealthResponse(ok=True, fleet_total=total, fleet_critical=critical)


async def serve(state: BotState, host: str, port: int) -> grpc.aio.Server:
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    alert_pb2_grpc.add_AlertServiceServicer_to_server(AlertService(state), server)
    server.add_insecure_port(f"{host}:{port}")
    await server.start()
    logger.info("PRATYAKSA Telegram bot gRPC server listening on %s:%s", host, port)
    return server

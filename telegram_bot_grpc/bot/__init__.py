"""PRATYAKSA Telegram bot — gRPC alert service + Telegram long-polling.

Python port of ``telegram_bot_grpc`` (originally Rust + tonic).  Two
concurrent responsibilities:

1. A gRPC ``AlertService`` server (port 50051) that the backend/frontend call
   to deliver a critical-unit alert to every subscribed Telegram chat.
2. A Telegram long-polling loop (``getUpdates``) handling ``/start``, ``/status``,
   ``/detail``, ``/pratyaksa``, ``/unit <id>``, ``/menu`` and ``/down`` plus the
   inline menu keyboards.
"""

from .config import BotConfig
from .state import BotState

__all__ = ["BotConfig", "BotState"]

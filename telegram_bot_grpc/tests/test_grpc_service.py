"""Tests for the gRPC AlertService (stubbed state, no Telegram network)."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.proto_loader import ensure_stubs
from bot.grpc_server import AlertService

alert_pb2, _ = ensure_stubs()


class FakeState:
    def __init__(self):
        self.bot_token = "test-token"
        self.fleet: dict = {}
        self.subscribers: set[int] = set()
        self.sent: list[tuple[int, str]] = []

        class _Cfg:
            wo_link_base = "example.com"

        self.config = _Cfg()

    def subscriber_list(self):
        return list(self.subscribers)

    async def send_message(self, chat_id, text):
        self.sent.append((chat_id, text))


class FakeContext:
    def __init__(self):
        self.aborted = None

    async def abort(self, code, message):
        self.aborted = (code, message)
        raise RuntimeError(message)


@pytest.mark.asyncio
async def test_send_alert_success():
    state = FakeState()
    state.subscribers.add(123)
    svc = AlertService(state)
    req = alert_pb2.AlertRequest(
        asset_id="WA600-001", model="wheel_loader", lokasi="Pit", status="CRITICAL",
        rul="42", shap1="a", shap2="b", part_name="p", part_no="n", stok="5",
    )
    ctx = FakeContext()
    resp = await svc.SendAlert(req, ctx)
    assert resp.success is True
    assert resp.asset_id == "WA600-001"
    assert len(state.sent) == 1
    assert "WA600-001" in state.sent[0][1]


@pytest.mark.asyncio
async def test_send_alert_no_subscribers():
    state = FakeState()
    svc = AlertService(state)
    req = alert_pb2.AlertRequest(asset_id="X", status="CRITICAL")
    ctx = FakeContext()
    with pytest.raises(RuntimeError):
        await svc.SendAlert(req, ctx)
    assert ctx.aborted is not None


@pytest.mark.asyncio
async def test_health_check_counts():
    state = FakeState()
    state.fleet = {
        "A": {"risk_level": "CRITICAL"},
        "B": {"risk_level": "NORMAL"},
        "C": {"risk_level": "critical"},
    }
    svc = AlertService(state)
    resp = await svc.HealthCheck(alert_pb2.HealthRequest(), FakeContext())
    assert resp.ok is True
    assert resp.fleet_total == 3
    assert resp.fleet_critical == 2

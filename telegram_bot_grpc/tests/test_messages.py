"""Unit tests for bot message builders (pure functions)."""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import messages as msg


def test_esc_html():
    assert msg.esc("a<b>&c") == "a&lt;b&gt;&amp;c"


def test_normalize_base():
    assert msg.normalize_base("") == "http://localhost"
    assert msg.normalize_base("http://x/") == "http://x"
    assert msg.normalize_base("example.com") == "https://example.com"


def test_build_alert_message_contains_fields():
    m = msg.build_alert_message(
        {
            "asset_id": "WA600-001",
            "model": "wheel_loader",
            "lokasi": "Pit A",
            "status": "CRITICAL",
            "rul": "42",
            "shap1": "vibration",
            "shap2": "coolant",
            "part_name": "Brake Pad",
            "part_no": "BP-01",
            "stok": "5",
        },
        "example.com",
    )
    assert "WA600-001" in m
    assert "CRITICAL" in m
    assert "https://example.com/wo/create/WA600-001" in m
    assert "Brake Pad" in m


def test_fleet_summary():
    m = msg.build_fleet_summary(
        {"critical": 2, "warning": 3, "normal": 10, "rusak": 1, "total": 16}
    )
    assert "CRITICAL : 2" in m
    assert "Total Unit : 16" in m


def test_pratyaksa_status():
    m = msg.build_pratyaksa_status(
        {"mode": "simulasi", "fleet_count": 6,
         "last_health_check": "1s ago", "last_fleet_poll": "2s ago"}
    )
    assert "🟡" in m
    assert "<b>simulasi</b>" in m


def test_unit_detail():
    m = msg.build_unit_detail(
        "simulasi",
        {
            "asset_id": "HD785-001",
            "equipment_type": "haul_truck",
            "risk_level": "WARNING",
            "lstm_rul_hours": 512.4,
            "rul_uncertainty": 42.0,
            "model_agreement": True,
            "drift_status": {"drift_detected": False},
            "digital_twin": {"brake_twin_rul": 300.0, "hydraulic_twin_rul": 400.0},
            "processed_at": 1719400000.0,
        },
    )
    assert "HD785-001" in m
    assert "WARNING" in m
    assert "512" in m


def test_unit_detail_includes_last_processed():
    m = msg.build_unit_detail("live", {"asset_id": "X", "processed_at": 1719400000.0})
    assert "Last processed" in m
    assert "UTC" in m
    # Missing/invalid processed_at degrades to N/A.
    m2 = msg.build_unit_detail("live", {"asset_id": "X"})
    assert "Last processed: N/A" in m2 or "Last processed:</b> N/A" in m2


def test_format_processed_at():
    assert msg.format_processed_at(0) == "N/A"
    assert msg.format_processed_at(None) == "N/A"
    assert msg.format_processed_at("bad") == "N/A"
    out = msg.format_processed_at(1719400000.0)
    assert out.endswith("UTC")
    assert out.startswith("202")


def test_detail_report():
    fleet = [
        {"asset_id": "A1", "equipment_type": "haul_truck", "risk_level": "NORMAL",
         "lstm_rul_hours": 800.0, "drift_detected": False, "model_agreement": True},
        {"asset_id": "A2", "equipment_type": "dozer", "risk_level": "CRITICAL",
         "lstm_rul_hours": 100.0, "drift_detected": True, "model_agreement": False},
    ]
    m = msg.build_detail_report("SUMMARY", "live", 450.0, fleet)
    assert "SUMMARY" in m
    assert "A1" in m and "A2" in m
    assert "Rata-rata RUL" in m


def test_menu_keyboard_shape():
    kb = msg.start_menu_keyboard()
    assert isinstance(kb, list)
    assert all("callback_data" in b for row in kb for b in row)

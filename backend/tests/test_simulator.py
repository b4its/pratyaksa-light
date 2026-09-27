"""Unit tests: simulator determinism & contract parity."""

from __future__ import annotations

from app.pratyaksa import simulator
from app.schemas.pratyaksa import FEATURE_NAMES, PredictRequest


def test_generate_fleet_stable_shape():
    fleet = simulator.generate_fleet()
    assert len(fleet) == 6
    for asset in fleet:
        assert asset.asset_id
        assert asset.risk_level in ("NORMAL", "WARNING", "CRITICAL")
        assert 0.0 <= asset.lstm_rul_hours <= 2000.0


def test_generate_result_has_contract_fields():
    result = simulator.generate_result("HD785-001")
    for key in (
        "asset_id",
        "equipment_type",
        "xgb_anomaly_class",
        "xgb_anomaly_label",
        "lstm_rul_hours",
        "risk_level",
        "risk_class",
        "model_agreement",
        "digital_twin",
        "drift_status",
        "latency_ms",
    ):
        assert key in result
    assert result["equipment_type"] == "haul_truck"
    assert result["xgb_anomaly_label"] in ("NORMAL", "WARNING", "CRITICAL")


def test_features_match_feature_names():
    resp = simulator.generate_features()
    assert resp["total"] == 37
    assert resp["features"] == FEATURE_NAMES
    assert len(FEATURE_NAMES) == 37


def test_generate_workorder_normalises_component():
    resp = simulator.generate_workorder("invalid", 0.5)
    assert resp.component == "brake"
    assert resp.status == "CREATED"
    assert resp.work_order_id.startswith("WO-SIM-")


def test_generate_predict():
    req = PredictRequest(asset_id="PC2000-001", equipment_type="excavator", timestamp="now", features=[0.0] * 37)
    resp = simulator.generate_predict(req)
    assert resp.asset_id == "PC2000-001"
    assert resp.risk_level in ("NORMAL", "WARNING", "CRITICAL")


def test_generate_explain_shape():
    exp = simulator.generate_explain()
    assert exp["prediction_id"] == "sim-000000"
    assert len(exp["shap_values"]) == 8

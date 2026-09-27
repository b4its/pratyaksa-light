"""Unit tests: health analytics derivations."""

from __future__ import annotations

from app.services import health_analytics as ha


def _unit(code="EXC-320-01", status="SEHAT", health=96, jenis="Caterpillar Excavator 320"):
    return {
        "id": "00000000-0000-0000-0000-000000000001",
        "code": code,
        "status": status,
        "health": health,
        "jenis_alat_berat_nama": jenis,
        "img_url": None,
        "model3d_url": None,
    }


def test_classify_status_thresholds():
    assert ha.classify_status(85, 55, 80, 65, 27.5, 20, 0.05, 0.5, 0) == "NORMAL"
    assert ha.classify_status(105, 55, 80, 65, 27.5, 20, 0.05, 0.5, 0) == "WARNING"
    assert ha.classify_status(115, 20, 80, 65, 27.5, 20, 0.05, 0.5, 0) == "CRITICAL"


def test_risk_level_bands():
    assert ha.risk_level(10) == "LOW"
    assert ha.risk_level(45) == "MEDIUM"
    assert ha.risk_level(65) == "HIGH"
    assert ha.risk_level(90) == "CRITICAL"


def test_unit_kind_and_slug():
    assert ha.unit_kind("PC2000 excavator") == "Excavator"
    assert ha.equipment_type_slug("PC2000 excavator") == "excavator"
    assert ha.equipment_type_slug("Scania Dump Truck") == "haul_truck"
    assert ha.equipment_type_slug("Komatsu Dozer") == "dozer"


def test_derive_telemetry_shape():
    t = ha.derive_telemetry(_unit())
    for key in (
        "component_type",
        "eng_coolant_temp_c",
        "status_label",
        "rul_hours",
        "delta_eng_temp",
    ):
        assert key in t
    assert 0 <= t["fault_code_severity"] <= 4


def test_derive_prediction_shape():
    p = ha.derive_prediction(_unit(status="CRITICAL", health=40))
    assert p["xgb_anomaly_class"] == 2
    assert p["risk_level"] == "CRITICAL"
    assert set(p["digital_twin"]) == {"brake_twin_rul", "bearing_twin_rul", "hydraulic_twin_rul"}


def test_derive_unit_analysis_full_payload():
    a = ha.derive_unit_analysis(_unit())
    assert set(
        [
            "unit",
            "risk_score",
            "risk_level",
            "sensor_readings",
            "component_health",
            "rul_prediction",
            "shap_contributions",
            "sensor_history",
            "telemetry",
            "prediction",
            "operational",
        ]
    ).issubset(a.keys())
    assert len(a["component_health"]) == 6
    assert len(a["sensor_history"]) == 24

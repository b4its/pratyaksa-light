"""Integration tests: pratyaksa simulator endpoints (require PostgreSQL/MongoDB)."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health_endpoint(client):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "Pratyaksa Backend"


@pytest.mark.asyncio
async def test_pratyaksa_status_and_fleet(client):
    resp = await client.get("/api/v1/pratyaksa/status")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["mode"] == "simulasi"
    assert data["fleet_count"] > 0
    assert data["generated_at"].endswith("ago")

    fleet = await client.get("/api/v1/pratyaksa/fleet")
    assert fleet.status_code == 200
    assert "fleet" in fleet.json()["data"]


@pytest.mark.asyncio
async def test_pratyaksa_mode_switch_is_simulasi_only(client):
    resp = await client.post("/api/v1/pratyaksa/mode", json={"mode": "live"})
    assert resp.status_code == 200
    assert resp.json()["data"]["mode"] == "simulasi"


@pytest.mark.asyncio
async def test_pratyaksa_predict_requires_37_features(client):
    bad = await client.post(
        "/api/v1/pratyaksa/predict",
        json={
            "asset_id": "X",
            "equipment_type": "excavator",
            "timestamp": "now",
            "features": [1.0, 2.0],
        },
    )
    assert bad.status_code == 400
    assert bad.json()["expected"] == 37

    good = await client.post(
        "/api/v1/pratyaksa/predict",
        json={
            "asset_id": "X",
            "equipment_type": "excavator",
            "timestamp": "now",
            "features": [1.0] * 37,
        },
    )
    assert good.status_code == 200
    assert good.json()["mode"] == "simulasi"


@pytest.mark.asyncio
async def test_features_endpoint(client):
    resp = await client.get("/api/v1/pratyaksa/features")
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 37


@pytest.mark.asyncio
async def test_protected_route_requires_token(client):
    resp = await client.get("/api/v1/unit-tambang")
    assert resp.status_code == 401
    assert resp.json()["status"] == "error"

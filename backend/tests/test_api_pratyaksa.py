"""Integration tests: live API endpoints (require PostgreSQL/MongoDB)."""

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
    assert resp.json()["data"]["mode"] in ("live", "simulasi")

    fleet = await client.get("/api/v1/pratyaksa/fleet")
    assert fleet.status_code == 200
    assert "fleet" in fleet.json()["data"]


@pytest.mark.asyncio
async def test_pratyaksa_mode_switch(client):
    resp = await client.post("/api/v1/pratyaksa/mode", json={"mode": "simulasi"})
    assert resp.status_code == 200
    assert resp.json()["data"]["mode"] == "simulasi"

    reset = await client.post("/api/v1/pratyaksa/mode", json={"reset": True})
    assert reset.status_code == 200


@pytest.mark.asyncio
async def test_pratyaksa_predict_requires_37_features(client):
    await client.post("/api/v1/pratyaksa/mode", json={"mode": "simulasi"})
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


@pytest.mark.asyncio
async def test_features_endpoint(client):
    await client.post("/api/v1/pratyaksa/mode", json={"mode": "simulasi"})
    resp = await client.get("/api/v1/pratyaksa/features")
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 37


@pytest.mark.asyncio
async def test_protected_route_requires_token(client):
    resp = await client.get("/api/v1/unit-tambang")
    assert resp.status_code == 401
    assert resp.json()["status"] == "error"

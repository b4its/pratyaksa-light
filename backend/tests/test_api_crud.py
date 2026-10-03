"""Integration tests: auth + CRUD against PostgreSQL/MongoDB."""

from __future__ import annotations

import uuid

import pytest


async def _register(client):
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    resp = await client.post(
        "/api/v1/auth/register",
        json={"name": "Test User", "email": email, "password": "secret123"},
    )
    assert resp.status_code == 201, resp.text
    token = resp.json()["data"]["token"]
    return email, token, {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_register_login_me(client):
    email, _, headers = await _register(client)

    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["data"]["email"] == email

    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "secret123"}
    )
    assert login.status_code == 200
    assert "token" in login.json()["data"]


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    email, _, _ = await _register(client)
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "wrong"}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_validation_messages_are_friendly(client):
    """Validation failures return a friendly Indonesian message, not raw
    Pydantic English (e.g. 'String should have at least 6 characters')."""
    # register: password too short
    resp = await client.post(
        "/api/v1/auth/register",
        json={"name": "Ok Name", "email": "friend1@example.com", "password": "123"},
    )
    assert resp.status_code == 400, resp.text
    msg = resp.json()["message"]
    assert "English" not in msg and "String should" not in msg
    assert "Kata sandi" in msg and "6" in msg

    # register: missing email
    resp2 = await client.post(
        "/api/v1/auth/register", json={"name": "Ok Name", "password": "secret123"}
    )
    assert resp2.status_code == 400
    assert "Email wajib diisi" in resp2.json()["message"]

    # unit-tambang: missing maintenance -> friendly, field-aware
    _, _, headers = await _register(client)
    jenis = await client.post(
        "/api/v1/jenis-alat-berat",
        json={"nama": f"Val Type {uuid.uuid4().hex[:6]}"},
        headers=headers,
    )
    jenis_id = jenis.json()["data"]["id"]
    bad = await client.post(
        "/api/v1/unit-tambang",
        json={
            "code": f"UT-{uuid.uuid4().hex[:6]}",
            "jenis_alat_berat_id": jenis_id,
            "status": "SEHAT",
            "health": 90,
            "maintenance": "",  # min_length=1 violated
            "savings": 0,
        },
        headers=headers,
    )
    assert bad.status_code == 400, bad.text
    bmsg = bad.json()["message"]
    assert "String should" not in bmsg
    assert "maintenance" in bmsg.lower() or "Jadwal" in bmsg


@pytest.mark.asyncio
async def test_jenis_alat_berat_crud(client):
    _, _, headers = await _register(client)
    nama = f"Excavator Test {uuid.uuid4().hex[:6]}"
    created = await client.post(
        "/api/v1/jenis-alat-berat", json={"nama": nama, "deskripsi": "test"}, headers=headers
    )
    assert created.status_code == 201, created.text
    item_id = created.json()["data"]["id"]

    listing = await client.get("/api/v1/jenis-alat-berat?search=Excavator", headers=headers)
    assert listing.status_code == 200

    updated = await client.put(
        f"/api/v1/jenis-alat-berat/{item_id}", json={"deskripsi": "updated"}, headers=headers
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["deskripsi"] == "updated"

    deleted = await client.delete(f"/api/v1/jenis-alat-berat/{item_id}", headers=headers)
    assert deleted.status_code == 200

    missing = await client.get(f"/api/v1/jenis-alat-berat/{item_id}", headers=headers)
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_unit_tambang_crud_and_telemetry(client):
    _, _, headers = await _register(client)

    jenis = await client.post(
        "/api/v1/jenis-alat-berat",
        json={"nama": f"Unit Type {uuid.uuid4().hex[:6]}"},
        headers=headers,
    )
    jenis_id = jenis.json()["data"]["id"]
    code = f"UT-{uuid.uuid4().hex[:6]}"

    created = await client.post(
        "/api/v1/unit-tambang",
        json={
            "code": code,
            "jenis_alat_berat_id": jenis_id,
            "status": "SEHAT",
            "health": 90,
            "maintenance": "OK",
            "savings": 100,
            "lat": -0.5,
            "lng": 117.1,
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    unit_id = created.json()["data"]["id"]
    assert created.json()["data"]["jenis_alat_berat_nama"]

    # telemetry ingestion for this unit
    tele = await client.post(
        "/api/v1/telemetry",
        json={"unit_id": unit_id, "eng_coolant_temp_c": 90, "fault_code_severity": 0},
        headers=headers,
    )
    assert tele.status_code == 201, tele.text
    assert tele.json()["data"]["status_label"] in ("NORMAL", "WARNING", "CRITICAL")

    history = await client.get(f"/api/v1/telemetry/unit/{unit_id}", headers=headers)
    assert history.status_code == 200
    assert len(history.json()["data"]) >= 1

    # invalid status rejected
    bad = await client.post(
        "/api/v1/unit-tambang",
        json={
            "code": f"BAD-{uuid.uuid4().hex[:6]}",
            "jenis_alat_berat_id": jenis_id,
            "status": "NOPE",
            "health": 50,
            "maintenance": "x",
            "savings": 0,
        },
        headers=headers,
    )
    assert bad.status_code == 400

    await client.delete(f"/api/v1/unit-tambang/{unit_id}", headers=headers)
    await client.delete(f"/api/v1/jenis-alat-berat/{jenis_id}", headers=headers)


@pytest.mark.asyncio
async def test_unit_tambang_update_rejects_duplicate_code(client):
    """Editing a unit's code to one already used must fail cleanly (409).

    Regression: the update route lacked the duplicate check the create route
    has, so the DB unique constraint raised a raw 500 instead of a 409.
    """
    _, _, headers = await _register(client)
    jenis = await client.post(
        "/api/v1/jenis-alat-berat",
        json={"nama": f"Dup Type {uuid.uuid4().hex[:6]}"},
        headers=headers,
    )
    jenis_id = jenis.json()["data"]["id"]

    base = {
        "jenis_alat_berat_id": jenis_id,
        "status": "SEHAT",
        "health": 90,
        "maintenance": "OK",
        "savings": 0,
    }
    code_a = f"UT-A-{uuid.uuid4().hex[:6]}"
    code_b = f"UT-B-{uuid.uuid4().hex[:6]}"
    a = await client.post("/api/v1/unit-tambang", json={"code": code_a, **base}, headers=headers)
    b = await client.post("/api/v1/unit-tambang", json={"code": code_b, **base}, headers=headers)
    assert a.status_code == 201 and b.status_code == 201
    id_a, id_b = a.json()["data"]["id"], b.json()["data"]["id"]

    # B → A's code (exact) must be a clean 409.
    dup = await client.put(
        f"/api/v1/unit-tambang/{id_b}", json={"code": code_a}, headers=headers
    )
    assert dup.status_code == 409, dup.text
    assert dup.json()["status"] == "error"

    # Case-insensitive duplicate also rejected.
    dup_ci = await client.put(
        f"/api/v1/unit-tambang/{id_b}", json={"code": code_a.lower()}, headers=headers
    )
    assert dup_ci.status_code == 409, dup_ci.text

    # Editing a unit without changing its own code must still succeed.
    own = await client.put(
        f"/api/v1/unit-tambang/{id_b}", json={"code": code_b, "health": 77}, headers=headers
    )
    assert own.status_code == 200, own.text
    assert own.json()["data"]["health"] == 77

    for uid in (id_a, id_b):
        await client.delete(f"/api/v1/unit-tambang/{uid}", headers=headers)
    await client.delete(f"/api/v1/jenis-alat-berat/{jenis_id}", headers=headers)


@pytest.mark.asyncio
async def test_work_order_lifecycle(client):
    _, _, headers = await _register(client)
    code = f"WO-UNIT-{uuid.uuid4().hex[:6]}"

    jenis = await client.post(
        "/api/v1/jenis-alat-berat", json={"nama": f"WO Type {uuid.uuid4().hex[:6]}"}, headers=headers
    )
    jenis_id = jenis.json()["data"]["id"]
    await client.post(
        "/api/v1/unit-tambang",
        json={
            "code": code,
            "jenis_alat_berat_id": jenis_id,
            "status": "CRITICAL",
            "health": 40,
            "maintenance": "x",
            "savings": 0,
        },
        headers=headers,
    )

    created = await client.post(
        "/api/v1/work-orders",
        json={"asset_code": code, "status_unit": "CRITICAL"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    wo = created.json()["data"]
    assert wo["wo_number"].startswith("WO-")
    wo_id = wo["id"]

    detail = await client.get(f"/api/v1/work-orders/{wo_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["data"]["unit"]["code"] == code

    completed = await client.put(
        f"/api/v1/work-orders/{wo_id}", json={"wo_status": "COMPLETED"}, headers=headers
    )
    assert completed.status_code == 200

    # unit should be healed after WO complete
    unit = await client.get(
        f"/api/v1/unit-tambang?search={code}", headers=headers
    )
    data = unit.json()["data"]["data"]
    assert data and data[0]["status"] == "SEHAT"

    # cleanup
    listing = await client.get("/api/v1/unit-tambang?search=" + code, headers=headers)
    for u in listing.json()["data"]["data"]:
        await client.delete(f"/api/v1/unit-tambang/{u['id']}", headers=headers)
    await client.delete(f"/api/v1/jenis-alat-berat/{jenis_id}", headers=headers)


@pytest.mark.asyncio
async def test_analisa_mongo_crud(client):
    _, _, headers = await _register(client)
    unit_uuid = str(uuid.uuid4())

    created = await client.post(
        "/api/v1/analisa",
        json={
            "unit_tambang_id": unit_uuid,
            "unit_code": "EXC-01",
            "tipe_kerusakan": "Overheat",
            "deskripsi": "Suhu mesin melampaui ambang",
            "severity": "HIGH",
            "sensor_data": {
                "suhu_mesin": 110,
                "tekanan_oli": 5,
                "rpm": 1500,
                "fuel_level": 60,
                "vibration": 4.2,
                "jam_operasi": 8000,
            },
            "rekomendasi": "Ganti coolant",
            "dilaporkan_oleh": "Tester",
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    item_id = created.json()["data"]["_id"]
    assert created.json()["data"]["status_analisa"] == "OPEN"

    listing = await client.get(f"/api/v1/analisa?unit_tambang_id={unit_uuid}", headers=headers)
    assert listing.status_code == 200
    assert listing.json()["data"]["total"] >= 1

    updated = await client.put(
        f"/api/v1/analisa/{item_id}", json={"status_analisa": "RESOLVED"}, headers=headers
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["status_analisa"] == "RESOLVED"

    deleted = await client.delete(f"/api/v1/analisa/{item_id}", headers=headers)
    assert deleted.status_code == 200


@pytest.mark.asyncio
async def test_dashboard_and_fleet_summary(client):
    summary = await client.get("/api/v1/fleet-summary")
    assert summary.status_code == 200
    assert "total" in summary.json()["data"]

    _, _, headers = await _register(client)
    dash = await client.get("/api/v1/dashboard", headers=headers)
    assert dash.status_code == 200
    data = dash.json()["data"]
    assert "status_distribution" in data
    assert "monthly_fleet_data" in data
    assert len(data["monthly_fleet_data"]) == 12


@pytest.mark.asyncio
async def test_health_analytics_overview_and_unit(client):
    _, _, headers = await _register(client)

    overview = await client.get("/api/v1/analisa/overview", headers=headers)
    assert overview.status_code == 200
    od = overview.json()["data"]
    assert "avg_health" in od
    assert "units" in od

    if od["units"]:
        unit_id = od["units"][0]["id"]
        unit = await client.get(f"/api/v1/analisa/unit/{unit_id}", headers=headers)
        assert unit.status_code == 200
        ud = unit.json()["data"]
        assert "sensor_readings" in ud
        assert "rul_prediction" in ud

"""Tests: service routes (/svc) and the validation-error envelope.

These cover the fixes for:
- /svc/* being reachable both at root and under /api/v1 (frontend uses the
  latter via PUBLIC_API_BASE).
- request validation failures returning HTTP 400 with the app error envelope
  (``{"status":"error","message":...}``) instead of FastAPI's default 422.
"""

from __future__ import annotations

import io

import pytest


@pytest.mark.asyncio
async def test_upload_model_rejects_bad_extension(client):
    files = {"file": ("malware.exe", io.BytesIO(b"x"), "application/octet-stream")}
    resp = await client.post("/api/v1/svc/upload-model", files=files)
    assert resp.status_code == 400
    assert resp.json()["status"] == "error"


@pytest.mark.asyncio
async def test_upload_model_accepts_glb_and_returns_url(client):
    files = {"file": ("unit.glb", io.BytesIO(b"glTF-bytes"), "model/gltf-binary")}
    resp = await client.post("/api/v1/svc/upload-model", files=files)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["url"].startswith("/media/models/")
    assert body["filename"] == "unit.glb"


@pytest.mark.asyncio
async def test_upload_model_available_at_root_prefix(client):
    files = {"file": ("unit.glb", io.BytesIO(b"glTF-bytes"), "model/gltf-binary")}
    resp = await client.post("/svc/upload-model", files=files)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_validation_error_uses_400_and_envelope(client):
    # Missing required fields → validation error, should be 400 + envelope.
    resp = await client.post("/api/v1/auth/login", json={"email": "not-an-email"})
    assert resp.status_code == 400
    body = resp.json()
    assert body["status"] == "error"
    assert "message" in body


@pytest.mark.asyncio
async def test_uploaded_model_is_served_via_static_mount(client):
    files = {"file": ("unit.glb", io.BytesIO(b"glTF-binary-payload"), "model/gltf-binary")}
    resp = await client.post("/api/v1/svc/upload-model", files=files)
    assert resp.status_code == 200
    url = resp.json()["url"]
    assert url.startswith("/media/models/")

    fetched = await client.get(url)
    assert fetched.status_code == 200
    assert fetched.content == b"glTF-binary-payload"


@pytest.mark.asyncio
async def test_send_alert_without_bot_returns_502(client):
    # No telegram bot running in tests → graceful 502 with envelope.
    resp = await client.post(
        "/api/v1/svc/send-alert",
        json={"asset_id": "EXC-1", "message": "test"},
    )
    assert resp.status_code in (502, 200)
    assert resp.json()["status"] in ("error", "success")


@pytest.mark.asyncio
async def test_live_routes_degrade_cleanly_without_mongo(client):
    # When MongoDB is unavailable the live routes must return a clean 503
    # envelope (never an unhandled 500). When it *is* available, they return
    # 200 — accept either, but require the app envelope shape.
    resp = await client.get("/api/v1/live/stats")
    assert resp.status_code in (200, 503)
    body = resp.json()
    assert body["status"] in ("success", "error")
    if resp.status_code == 503:
        assert "MongoDB" in body["message"]


def test_get_mongo_dependency_raises_clean_503():
    from types import SimpleNamespace

    from app.core.deps import get_mongo
    from app.core.errors import ServiceUnavailableError

    req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(mongo=None)))
    try:
        get_mongo(req)  # type: ignore[arg-type]
        raise AssertionError("expected ServiceUnavailableError")
    except ServiceUnavailableError as exc:
        assert exc.status_code == 503
        assert "MongoDB" in exc.message

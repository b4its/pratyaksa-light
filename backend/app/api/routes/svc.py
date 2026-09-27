"""Service routes mirroring the Nuxt ``/svc`` endpoints.

- ``POST /svc/upload-model``  → store a 3D model file and return its URL.
- ``POST /svc/send-alert``    → forward an alert to the Telegram bot.

The original Nuxt frontend hosted these; we keep them on the backend so the
Svelte frontend stays thin.  The Telegram alert is dispatched over gRPC to the
existing Rust ``telegram_bot_grpc`` service (low latency), matching the original
design, with a clear error if the bot is unreachable.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/svc", tags=["svc"])

ALLOWED_EXT = [".glb", ".gltf"]
MAX_BYTES = 50 * 1024 * 1024  # 50 MB
MEDIA_DIR = Path(os.environ.get("MEDIA_DIR", "./media/models"))


@router.post("/upload-model")
async def upload_model(file: UploadFile = File(...)) -> JSONResponse:
    original = (file.filename or "model.glb").lower()
    ext = os.path.splitext(original)[1]
    if ext not in ALLOWED_EXT:
        return JSONResponse(
            status_code=400, content={"status": "error", "message": "Format harus .glb atau .gltf."}
        )

    data = await file.read()
    if len(data) > MAX_BYTES:
        return JSONResponse(
            status_code=413,
            content={"status": "error", "message": "Ukuran file maksimal 50 MB."},
        )

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = f"{int(__import__('time').time())}-{uuid.uuid4().hex[:8]}{ext}"
    (MEDIA_DIR / safe_name).write_bytes(data)

    return JSONResponse(
        {
            "status": "success",
            "url": f"/media/models/{safe_name}",
            "filename": original,
            "size": len(data),
        }
    )


@router.post("/send-alert")
async def send_alert(request: Request) -> JSONResponse:
    body = await request.json()
    config = request.app.state.config
    target = os.environ.get("TELEGRAM_GRPC_TARGET", "127.0.0.1:50051")

    # Normalize payload to strings (proto AlertRequest is all strings).
    payload = {k: ("" if v is None else str(v)) for k, v in (body or {}).items()}

    try:
        from app.services.telegram import send_alert_grpc
    except Exception:  # pragma: no cover
        send_alert_grpc = None

    if send_alert_grpc is None:
        return JSONResponse(
            status_code=502,
            content={
                "status": "error",
                "message": "gRPC client tidak tersedia. Instal grpcio untuk mengaktifkan alert.",
            },
        )

    try:
        result = await send_alert_grpc(target, payload)
        if not result.get("success"):
            return JSONResponse(
                status_code=502,
                content={
                    "status": "error",
                    "message": result.get("message", "Service bot menolak alert."),
                },
            )
        return JSONResponse({"status": "success", "upstream": result})
    except Exception as exc:
        return JSONResponse(
            status_code=502,
            content={
                "status": "error",
                "message": f"Gagal menghubungi service bot via gRPC ({target}): {exc}",
            },
        )


_ = config if "config" in dir() else None

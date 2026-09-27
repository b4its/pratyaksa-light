"""gRPC client to the telegram_bot_grpc service (optional dependency).

Uses ``grpcio`` if available; otherwise raises ImportError so callers can
degrade gracefully.  The proto is materialised and compiled once (lazily), the
generated stubs are cached, and a single channel per target is reused across
calls — mirroring the original Nuxt server route which cached its gRPC client.

The RPC is invoked in a thread executor so it does not block the event loop.
"""

from __future__ import annotations

import asyncio
import os
import threading
from typing import Any

try:
    import grpc

    _GRPC_AVAILABLE = True
except Exception:  # pragma: no cover - grpcio optional
    _GRPC_AVAILABLE = False


PROTO_PATH = "alert.proto"
_PROTO_DIR = os.environ.get("PRATYAKSA_PROTO_DIR", "/tmp/pratyaksa-proto")
DEFAULT_TARGET = os.environ.get("TELEGRAM_GRPC_TARGET", "127.0.0.1:50051")

_PROTO_SOURCE = """
syntax = "proto3";
package alert;

service AlertService {
  rpc SendAlert(AlertRequest) returns (AlertResponse);
  rpc HealthCheck(HealthRequest) returns (HealthResponse);
}

message AlertRequest {
  string asset_id  = 1;
  string model     = 2;
  string lokasi    = 3;
  string status    = 4;
  string rul       = 5;
  string shap1     = 6;
  string shap2     = 7;
  string part_name = 8;
  string part_no   = 9;
  string stok      = 10;
}

message AlertResponse {
  bool   success  = 1;
  string message  = 2;
  string asset_id = 3;
}

message HealthRequest {}

message HealthResponse {
  bool  ok             = 1;
  int32 fleet_total    = 2;
  int32 fleet_critical = 3;
}
"""

_ALERT_FIELDS = [
    "asset_id",
    "model",
    "lokasi",
    "status",
    "rul",
    "shap1",
    "shap2",
    "part_name",
    "part_no",
    "stok",
]

_stubs_lock = threading.Lock()
_stub_module: Any = None
_pb2_module: Any = None
_channels: dict[str, Any] = {}
_channel_lock = threading.Lock()


def _materialize_proto() -> None:
    os.makedirs(_PROTO_DIR, exist_ok=True)
    path = os.path.join(_PROTO_DIR, PROTO_PATH)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(_PROTO_SOURCE)


def _load_stubs() -> tuple[Any, Any, Any]:
    """Compile (once) and import the generated proto stubs.

    Returns ``(pb2, pb2_grpc, None)`` on success or ``(None, None, error)``.
    """
    global _stub_module, _pb2_module
    with _stubs_lock:
        if _stub_module is not None and _pb2_module is not None:
            return _pb2_module, _stub_module, None
        try:
            from grpc_tools import protoc

            _materialize_proto()
            protoc.main(
                (
                    "protoc",
                    f"-I{_PROTO_DIR}",
                    f"--python_out={_PROTO_DIR}",
                    f"--grpc_python_out={_PROTO_DIR}",
                    os.path.join(_PROTO_DIR, PROTO_PATH),
                )
            )
            import sys
            import importlib

            if _PROTO_DIR not in sys.path:
                sys.path.insert(0, _PROTO_DIR)
            _pb2_module = importlib.import_module("alert_pb2")
            _stub_module = importlib.import_module("alert_pb2_grpc")
            return _pb2_module, _stub_module, None
        except Exception as exc:  # pragma: no cover - build/runtime dependent
            return None, None, exc


def _get_channel(target: str) -> Any:
    with _channel_lock:
        channel = _channels.get(target)
        if channel is None:
            channel = grpc.insecure_channel(target)
            _channels[target] = channel
        return channel


def _map_grpc_error(exc: Exception, target: str) -> str:
    """Translate a gRPC error into an Indonesian, user-facing message."""
    code = None
    try:
        code = exc.code()  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover - not a grpc error
        code = None
    if code == grpc.StatusCode.UNAVAILABLE:
        return f"Service bot Telegram tidak dapat dihubungi ({target})."
    if code == grpc.StatusCode.DEADLINE_EXCEEDED:
        return "Service bot Telegram tidak merespons (timeout)."
    if code == grpc.StatusCode.FAILED_PRECONDITION:
        return "Bot Telegram menolak alert (token/kontak belum siap)."
    return f"Gagal menghubungi service bot via gRPC ({target}): {exc}"


def _sync_send_alert(target: str, payload: dict[str, str], timeout: float = 20.0) -> dict:
    if not _GRPC_AVAILABLE:
        raise ImportError("grpcio is not installed")

    pb2, pb2_grpc, error = _load_stubs()
    if error is not None:
        raise RuntimeError(f"Gagal menyiapkan stub gRPC: {error}")

    channel = _get_channel(target)
    stub = pb2_grpc.AlertServiceStub(channel)
    request = pb2.AlertRequest(**{k: payload.get(k, "") for k in _ALERT_FIELDS})
    resp = stub.SendAlert(request, timeout=timeout)
    return {"success": resp.success, "message": resp.message, "asset_id": resp.asset_id}


def _sync_health_check(target: str, timeout: float = 5.0) -> dict:
    if not _GRPC_AVAILABLE:
        raise ImportError("grpcio is not installed")

    pb2, pb2_grpc, error = _load_stubs()
    if error is not None:
        raise RuntimeError(f"Gagal menyiapkan stub gRPC: {error}")

    channel = _get_channel(target)
    stub = pb2_grpc.AlertServiceStub(channel)
    resp = stub.HealthCheck(pb2.HealthRequest(), timeout=timeout)
    return {
        "ok": resp.ok,
        "fleet_total": resp.fleet_total,
        "fleet_critical": resp.fleet_critical,
    }


async def send_alert_grpc(target: str, payload: dict[str, str]) -> dict:
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, _sync_send_alert, target, payload)
    except ImportError:
        raise
    except Exception as exc:  # noqa: BLE001 - normalise to friendly message
        raise RuntimeError(_map_grpc_error(exc, target)) from exc


async def health_check_grpc(target: str) -> dict:
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, _sync_health_check, target)
    except ImportError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(_map_grpc_error(exc, target)) from exc

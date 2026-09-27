"""gRPC client to the telegram_bot_grpc service (optional dependency).

Uses ``grpcio`` if available; otherwise raises ImportError so callers can
degrade gracefully.  The proto is defined inline to avoid shipping a separate
file (matching the original Nuxt server route which embedded the proto).

The RPC is invoked in a thread executor so it does not block the event loop.
"""

from __future__ import annotations

import asyncio
from typing import Any

try:
    import grpc

    _GRPC_AVAILABLE = True
except Exception:  # pragma: no cover - grpcio optional
    _GRPC_AVAILABLE = False


PROTO_PATH = "alert.proto"
_PROTO_DIR = "/tmp/pratyaksa-proto"

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


def _materialize_proto() -> str:
    import os

    os.makedirs(_PROTO_DIR, exist_ok=True)
    path = os.path.join(_PROTO_DIR, PROTO_PATH)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(_PROTO_SOURCE)
    return path


def _generate_stubs() -> tuple[Any, Any]:
    from grpc_tools import protoc

    proto_path = _materialize_proto()
    include = os.path.dirname(proto_path)
    protoc.main(
        (
            "protoc",
            f"-I{include}",
            f"--python_out={include}",
            f"--grpc_python_out={include}",
            proto_path,
        )
    )
    return proto_path, include


import os  # noqa: E402  (used by helpers above)


def _sync_send_alert(target: str, payload: dict[str, str], timeout: float = 20.0) -> dict:
    if not _GRPC_AVAILABLE:
        raise ImportError("grpcio is not installed")

    proto_path, include = _generate_stubs()
    import sys

    if include not in sys.path:
        sys.path.insert(0, include)

    import importlib

    alert_pb2 = importlib.import_module("alert_pb2")
    alert_pb2_grpc = importlib.import_module("alert_pb2_grpc")

    channel = grpc.insecure_channel(target)
    try:
        stub = alert_pb2_grpc.AlertServiceStub(channel)
        request = alert_pb2.AlertRequest(**{k: payload.get(k, "") for k in _ALERT_FIELDS})
        resp = stub.SendAlert(request, timeout=timeout)
        return {"success": resp.success, "message": resp.message, "asset_id": resp.asset_id}
    finally:
        channel.close()


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


async def send_alert_grpc(target: str, payload: dict[str, str]) -> dict:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _sync_send_alert, target, payload)

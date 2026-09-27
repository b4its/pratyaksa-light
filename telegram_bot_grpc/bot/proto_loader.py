"""Compile the alert.proto into Python stubs (cached under a build dir)."""

from __future__ import annotations

import importlib
import os
import sys

PROTO_DIR = os.path.join(os.path.dirname(__file__), "..", "proto")
GEN_DIR = os.path.join(os.path.dirname(__file__), "..", "_generated")


def ensure_stubs() -> tuple[object, object]:
    """Return (alert_pb2, alert_pb2_grpc), compiling from proto if needed."""
    proto_path = os.path.abspath(os.path.join(PROTO_DIR, "alert.proto"))
    gen_dir = os.path.abspath(GEN_DIR)
    os.makedirs(gen_dir, exist_ok=True)

    pb2 = os.path.join(gen_dir, "alert_pb2.py")
    if not os.path.exists(pb2):
        from grpc_tools import protoc

        rc = protoc.main(
            (
                "protoc",
                f"-I{os.path.dirname(proto_path)}",
                f"--python_out={gen_dir}",
                f"--grpc_python_out={gen_dir}",
                proto_path,
            )
        )
        if rc != 0:  # pragma: no cover
            raise RuntimeError(f"protoc gagal (rc={rc})")

    if gen_dir not in sys.path:
        sys.path.insert(0, gen_dir)

    alert_pb2 = importlib.import_module("alert_pb2")
    alert_pb2_grpc = importlib.import_module("alert_pb2_grpc")
    return alert_pb2, alert_pb2_grpc

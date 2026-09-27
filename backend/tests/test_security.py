"""Unit tests: password hashing & JWT."""

from __future__ import annotations

import time

import pytest

from app.core.config import AppConfig
from app.core.errors import UnauthorizedError
from app.core.security import create_token, decode_token, hash_password, verify_password


def test_password_roundtrip():
    h = hash_password("secret123")
    assert verify_password("secret123", h)
    assert not verify_password("wrong", h)


def test_seeded_rust_hash_verifies():
    # $2y$05$ hash seeded by the original Rust migration for "admin123"
    seed = "$2y$05$ZcuKmA4QskXogFHMv8gCWO1kOVSYRG.yQiJPDK9KE8gzaiJMvYQ/."
    assert verify_password("admin123", seed)


def test_jwt_roundtrip():
    config = AppConfig(jwt_secret="unit-test-secret", jwt_expiry_hours=1)
    token = create_token("user-1", "u@example.com", "admin", config)
    claims = decode_token(token, config)
    assert claims.sub == "user-1"
    assert claims.email == "u@example.com"
    assert claims.role == "admin"
    assert claims.exp > int(time.time())


def test_jwt_invalid_raises():
    config = AppConfig(jwt_secret="a", jwt_expiry_hours=1)
    token = create_token("u", "e", "r", config)
    with pytest.raises(UnauthorizedError):
        decode_token(token, AppConfig(jwt_secret="b"))


def test_password_verify_invalid_hash_returns_false():
    assert not verify_password("x", "not-a-hash")

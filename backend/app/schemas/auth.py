"""Pydantic schemas: auth & users."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Optional

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    name: Annotated[str, Field(min_length=2, max_length=100)]
    email: EmailStr
    password: Annotated[str, Field(min_length=6)]


class LoginRequest(BaseModel):
    email: EmailStr
    password: Annotated[str, Field(min_length=1)]


class UserPublic(BaseModel):
    id: str
    name: str
    email: str
    role: str
    created_at: datetime


class AuthResponse(BaseModel):
    token: str
    user: UserPublic


class UserRow(BaseModel):
    id: str
    name: str
    email: str
    password_hash: str
    role: str
    created_at: datetime
    updated_at: datetime


class ClaimsModel(BaseModel):
    sub: str
    email: str
    role: str
    exp: int
    iat: int

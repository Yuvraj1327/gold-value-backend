"""Auth schemas.

These map 1:1 onto the Supabase GoTrue REST API contract, since
`app/services/auth_service.py` proxies straight through to Supabase Auth.
"""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    name: str | None = Field(default=None, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class AuthUser(BaseModel):
    id: str
    email: str | None = None
    is_anonymous: bool = False
    role: str = "user"


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AuthUser


class LogoutRequest(BaseModel):
    access_token: str

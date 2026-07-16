"""Shared pytest fixtures.

Endpoint tests use FastAPI's dependency-override mechanism to swap real
DB-backed dependencies for lightweight fakes — this keeps the test suite
fast and independent of a live Postgres/Supabase instance, while unit
tests for pure logic (calculators, staleness rules) need no fixtures at
all.
"""
from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/test")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-jwt-secret-value-not-real")
os.environ.setdefault("ENABLE_SCHEDULER", "false")

import pytest
from fastapi.testclient import TestClient

from app.core.security import CurrentUser, get_current_user
from app.main import app


@pytest.fixture
def fake_user() -> CurrentUser:
    return CurrentUser(
        id="11111111-1111-1111-1111-111111111111", email="test@example.com", is_anonymous=False
    )


@pytest.fixture
def client(fake_user: CurrentUser) -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: fake_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

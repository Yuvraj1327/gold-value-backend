from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.exceptions import UpstreamServiceError, ValidationAppError
from app.schemas.auth import SignupRequest
from app.services.auth_service import AuthService


class _FakeUserRepository:
    async def upsert_profile(self, *, user_id, email, name):
        class _Profile:
            role = "user"

        return _Profile()


def _fake_async_client(mock_post: AsyncMock):
    """Builds a context-manager-compatible stand-in for `httpx.AsyncClient()`
    whose `.post` is the given AsyncMock — lets us control exactly what the
    "call to Supabase" returns/raises without a real network call."""
    fake_client = MagicMock()
    fake_client.post = mock_post
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=False)
    return fake_client


@pytest.mark.asyncio
async def test_signup_wraps_connection_errors_as_upstream_service_error():
    """Regression test: previously a DNS/connection failure reaching
    Supabase (e.g. misconfigured SUPABASE_URL) raised an unhandled
    httpx.ConnectError, surfacing as a raw 500 instead of a clean 502."""
    service = AuthService(_FakeUserRepository())
    mock_post = AsyncMock(side_effect=httpx.ConnectError("Name or service not known"))

    with patch("app.services.auth_service.httpx.AsyncClient", return_value=_fake_async_client(mock_post)):
        with pytest.raises(UpstreamServiceError):
            await service.signup(SignupRequest(email="jane@example.com", password="correcthorse123"))


@pytest.mark.asyncio
async def test_signup_with_email_confirmation_pending_gives_clear_message():
    """Regression test: when Supabase's "Confirm email" setting is on (the
    default for new projects), a successful signup response has no
    access_token/refresh_token until the user confirms — this previously
    raised an unhandled KeyError instead of a clear message."""
    service = AuthService(_FakeUserRepository())

    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = {
        "user": {"id": "11111111-1111-1111-1111-111111111111", "email": "jane@example.com"}
        # No "access_token" / "refresh_token" — confirmation pending.
    }
    mock_post = AsyncMock(return_value=fake_response)

    with patch("app.services.auth_service.httpx.AsyncClient", return_value=_fake_async_client(mock_post)):
        with pytest.raises(ValidationAppError, match="confirm your address"):
            await service.signup(SignupRequest(email="jane@example.com", password="correcthorse123"))


@pytest.mark.asyncio
async def test_signup_succeeds_with_full_session_response():
    service = AuthService(_FakeUserRepository())

    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = {
        "access_token": "token-abc",
        "refresh_token": "refresh-abc",
        "expires_in": 3600,
        "user": {"id": "11111111-1111-1111-1111-111111111111", "email": "jane@example.com"},
    }
    mock_post = AsyncMock(return_value=fake_response)

    with patch("app.services.auth_service.httpx.AsyncClient", return_value=_fake_async_client(mock_post)):
        result = await service.signup(SignupRequest(email="jane@example.com", password="correcthorse123"))

    assert result.access_token == "token-abc"
    assert result.user.email == "jane@example.com"
    assert result.user.role == "user"


@pytest.mark.asyncio
async def test_signup_400_error_body_is_parsed_safely_even_if_not_json():
    """Regression test: the 400 branch previously called response.json()
    twice and would raise if the body wasn't valid JSON at all."""
    service = AuthService(_FakeUserRepository())

    fake_response = MagicMock()
    fake_response.status_code = 400
    fake_response.json.side_effect = ValueError("not JSON")
    mock_post = AsyncMock(return_value=fake_response)

    with patch("app.services.auth_service.httpx.AsyncClient", return_value=_fake_async_client(mock_post)):
        with pytest.raises(ValidationAppError):
            await service.signup(SignupRequest(email="jane@example.com", password="correcthorse123"))

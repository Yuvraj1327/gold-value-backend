"""Auth service.

Signup/login/logout are implemented by calling Supabase's own GoTrue REST
API server-side. We intentionally do NOT reimplement password hashing or
session issuance — Supabase Auth already does this correctly and the
Flutter app also talks to Supabase directly for Google OAuth and anonymous
guest sign-in. These backend endpoints exist for clients that prefer a
single API surface (e.g. future web dashboard) and for consistent
centralized logging/rate-limiting of auth attempts.
"""
from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError, UpstreamServiceError, ValidationAppError
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AuthResponse, AuthUser, LoginRequest, SignupRequest

settings = get_settings()

_GOTRUE_HEADERS = {
    "apikey": settings.SUPABASE_ANON_KEY,
    "Content-Type": "application/json",
}


class AuthService:
    def __init__(self, user_repository: UserRepository) -> None:
        self._user_repository = user_repository
        self._base_url = f"{settings.SUPABASE_URL}/auth/v1"

    async def signup(self, payload: SignupRequest) -> AuthResponse:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{self._base_url}/signup",
                    headers=_GOTRUE_HEADERS,
                    json={
                        "email": payload.email,
                        "password": payload.password,
                        "data": {"name": payload.name} if payload.name else {},
                    },
                )
        except httpx.HTTPError as exc:
            raise UpstreamServiceError(
                "Could not reach the authentication provider. Check SUPABASE_URL/network."
            ) from exc
        return await self._handle_auth_response(response, fallback_name=payload.name)

    async def login(self, payload: LoginRequest) -> AuthResponse:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{self._base_url}/token?grant_type=password",
                    headers=_GOTRUE_HEADERS,
                    json={"email": payload.email, "password": payload.password},
                )
        except httpx.HTTPError as exc:
            raise UpstreamServiceError(
                "Could not reach the authentication provider. Check SUPABASE_URL/network."
            ) from exc
        return await self._handle_auth_response(response)

    async def logout(self, access_token: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{self._base_url}/logout",
                    headers={**_GOTRUE_HEADERS, "Authorization": f"Bearer {access_token}"},
                )
        except httpx.HTTPError as exc:
            raise UpstreamServiceError(
                "Could not reach the authentication provider. Check SUPABASE_URL/network."
            ) from exc
        # GoTrue returns 204 on success; treat 401 (already expired) as a no-op success too.
        if response.status_code not in (204, 401):
            raise UpstreamServiceError("Failed to sign out with the auth provider.")



    async def _handle_auth_response(
        self, response: httpx.Response, *, fallback_name: str | None = None
    ) -> AuthResponse:
        if response.status_code == 400:
            try:
                body = response.json()
            except ValueError:
                body = {}
            detail = body.get("error_description") or body.get("msg")
            raise ValidationAppError(detail or "Invalid signup/login request.")
        if response.status_code in (401, 403):
            raise UnauthorizedError("Invalid email or password.")
        if response.status_code >= 500:
            raise UpstreamServiceError("Authentication provider is currently unavailable.")
        if response.status_code >= 400:
            raise ValidationAppError("Could not complete the authentication request.")

        try:
            body = response.json()
        except ValueError as exc:
            raise UpstreamServiceError(
                "Authentication provider returned an unexpected response."
            ) from exc
        user_payload = body.get("user", {})
        email = user_payload.get("email")
        user_id = user_payload.get("id")
        role = "user"

        # Keep our public.users profile row in sync (idempotent upsert).
        if user_id and email:
            import uuid as uuid_module

            name = (user_payload.get("user_metadata") or {}).get("name") or fallback_name
            profile = await self._user_repository.upsert_profile(
                user_id=uuid_module.UUID(user_id), email=email, name=name
            )
            role = profile.role

        # If Supabase's "Confirm email" setting is enabled (the default for
        # new projects), a successful signup returns the created user but
        # NO session — access_token/refresh_token are absent until the
        # user clicks the confirmation link. Without this check, the dict
        # lookups below raised an unhandled KeyError (500) instead of a
        # clear, actionable message.
        if "access_token" not in body or "refresh_token" not in body:
            raise ValidationAppError(
                "Account created. Please check your email to confirm your address before signing in."
            )

        return AuthResponse(
            access_token=body["access_token"],
            refresh_token=body["refresh_token"],
            expires_in=body.get("expires_in", 3600),
            user=AuthUser(
                id=user_id,
                email=email,
                is_anonymous=bool(user_payload.get("is_anonymous", False)),
                role=role,
            ),
        )

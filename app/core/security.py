"""JWT verification for Supabase-issued access tokens.

The Flutter app authenticates directly against Supabase Auth (email,
Google OAuth, or anonymous guest sign-in) and attaches the resulting
Supabase access token as `Authorization: Bearer <token>` on every request
to this backend.

Supabase projects created after ~2024 use asymmetric ES256 JWT keys
(ECDSA P-256) instead of the legacy HS256 HMAC secret.  We now verify
tokens via the project's public JWKS endpoint
(`/auth/v1/.well-known/jwks.json`) so the backend works regardless of
which algorithm the project uses.  A short-lived in-memory cache avoids
a round-trip on every request; the cache is refreshed automatically when
a key-ID is not found (to handle key rotation).

The legacy `SUPABASE_JWT_SECRET` env-var is kept as a fallback: if the
JWKS fetch fails *and* the token carries `alg: HS256`, we fall back to
HMAC verification with the secret.  This ensures backwards compatibility
with self-hosted / local Supabase instances that still use HS256.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
from fastapi import Depends, Header
from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError

settings = get_settings()

# ---------------------------------------------------------------------------
# JWKS cache — fetched once, refreshed when a kid is missing or TTL expires
# ---------------------------------------------------------------------------
_JWKS_TTL_SECONDS = 3600  # refresh keys hourly


@dataclass
class _JwksCache:
    keys: dict[str, Any] = field(default_factory=dict)   # kid -> JWK dict
    raw: dict = field(default_factory=dict)               # full {"keys": [...]} dict
    fetched_at: float = 0.0
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def is_stale(self) -> bool:
        return (time.monotonic() - self.fetched_at) > _JWKS_TTL_SECONDS

    def load(self, jwks: dict) -> None:
        self.raw = jwks
        self.keys = {k["kid"]: k for k in jwks.get("keys", []) if "kid" in k}
        self.fetched_at = time.monotonic()


_jwks_cache = _JwksCache()

JWKS_URL = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"


async def _fetch_jwks() -> dict:
    """Fetch Supabase JWKS.  Raises UnauthorizedError on failure."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(JWKS_URL)
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        raise UnauthorizedError(
            "Could not fetch authentication keys from Supabase. "
            "Please try again later."
        ) from exc


async def _get_jwks(force_refresh: bool = False) -> dict:
    """Return the current JWKS dict, refreshing the cache as needed."""
    async with _jwks_cache._lock:
        if force_refresh or _jwks_cache.is_stale():
            jwks = await _fetch_jwks()
            _jwks_cache.load(jwks)
    return _jwks_cache.raw


async def warm_jwks_cache() -> None:
    """Pre-fetch keys at startup so the first request isn't slowed down."""
    try:
        await _get_jwks(force_refresh=True)
    except UnauthorizedError:
        # Non-fatal at startup — will retry on first authenticated request.
        pass


# ---------------------------------------------------------------------------
# Token decoding
# ---------------------------------------------------------------------------

def _get_token_header(token: str) -> dict:
    """Decode the JOSE header without verifying the signature."""
    try:
        return jwt.get_unverified_header(token)
    except JWTError as exc:
        raise UnauthorizedError("Malformed token header.") from exc


async def _decode_token(token: str) -> dict:
    """
    Verify a Supabase JWT and return its payload.

    Strategy:
    1. Inspect the token header to determine `alg` and `kid`.
    2. For asymmetric algs (ES256, RS256 …): verify against Supabase JWKS.
       - If the kid is absent from the cache, force-refresh once (key rotation).
    3. For HS256 (legacy / self-hosted): verify against `SUPABASE_JWT_SECRET`.
    """
    header = _get_token_header(token)
    alg = header.get("alg", "")
    kid = header.get("kid")

    # ------------------------------------------------------------------
    # Asymmetric algorithms  (ES256, RS256, EdDSA …)
    # ------------------------------------------------------------------
    if alg != "HS256":
        jwks = await _get_jwks()

        # If kid is present but not in cache, try a forced refresh first
        # (handles key rotation without restarting the server).
        if kid and kid not in _jwks_cache.keys:
            jwks = await _get_jwks(force_refresh=True)

        try:
            payload = jwt.decode(
                token,
                jwks,
                algorithms=[alg],
                audience="authenticated",
            )
        except JWTError as exc:
            raise UnauthorizedError("Invalid or expired token.") from exc
        return payload

    # ------------------------------------------------------------------
    # HS256 fallback (legacy secret-based Supabase projects)
    # ------------------------------------------------------------------
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except JWTError as exc:
        raise UnauthorizedError("Invalid or expired token.") from exc
    return payload


# ---------------------------------------------------------------------------
# Public FastAPI dependencies
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str | None
    is_anonymous: bool


def get_bearer_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("Missing or malformed Authorization header.")
    return authorization.split(" ", 1)[1].strip()


async def get_current_user(token: str = Depends(get_bearer_token)) -> CurrentUser:
    """Dependency that verifies the token and returns the authenticated user.

    Works uniformly for email/password, Google OAuth, and anonymous guest
    sessions — Supabase issues a valid JWT for all three; anonymous users
    simply carry `"is_anonymous": true` in the payload.
    """
    payload = await _decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Token missing subject claim.")

    return CurrentUser(
        id=user_id,
        email=payload.get("email"),
        is_anonymous=bool(payload.get("is_anonymous", False)),
    )


async def get_optional_user(
    authorization: str | None = Header(default=None),
) -> CurrentUser | None:
    """Same as get_current_user but returns None instead of raising.

    Used by endpoints like /gold-rate that are useful even to signed-out
    users but should still recognize a signed-in caller if present.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    try:
        payload = await _decode_token(authorization.split(" ", 1)[1].strip())
    except UnauthorizedError:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    return CurrentUser(
        id=user_id,
        email=payload.get("email"),
        is_anonymous=bool(payload.get("is_anonymous", False)),
    )

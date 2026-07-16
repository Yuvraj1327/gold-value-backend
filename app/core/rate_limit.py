"""Rate limiting via slowapi (a Flask-Limiter style wrapper for Starlette).

Limits are keyed by client IP by default, falling back gracefully when
behind a proxy (reads X-Forwarded-For if present). Per-route overrides are
applied with the `@limiter.limit(...)` decorator on individual endpoints
(see gold_rate.py, calculations.py) using the values from Settings.
"""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

settings = get_settings()


def _rate_limit_key(request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=_rate_limit_key, default_limits=[settings.RATE_LIMIT_DEFAULT])

"""Domain-level exceptions.

Repositories/services raise these instead of leaking SQLAlchemy or HTTPX
errors upward. The centralized exception handlers in `app/core/middleware.py`
translate each of these into a consistent JSON error response with the
correct HTTP status code.
"""
from __future__ import annotations


class AppError(Exception):
    """Base class for all application-level errors."""

    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)


class NotFoundError(AppError):
    status_code = 404
    error_code = "not_found"


class ValidationAppError(AppError):
    status_code = 422
    error_code = "validation_error"


class UnauthorizedError(AppError):
    status_code = 401
    error_code = "unauthorized"


class ForbiddenError(AppError):
    status_code = 403
    error_code = "forbidden"


class ConflictError(AppError):
    status_code = 409
    error_code = "conflict"


class UpstreamServiceError(AppError):
    """Raised when an external dependency (e.g. gold rate provider, Supabase Auth) fails."""

    status_code = 502
    error_code = "upstream_service_error"


class RateLimitExceededError(AppError):
    status_code = 429
    error_code = "rate_limit_exceeded"

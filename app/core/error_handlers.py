"""Centralized exception handling.

Every error path in the app — whether raised by a repository, a service,
or FastAPI/Pydantic itself — is funneled through here so API consumers
(the Flutter app) always receive the same JSON error envelope:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Stone weight cannot exceed gross weight.",
    "details": {}
  }
}
```
"""
from __future__ import annotations

import uuid

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppError
from app.core.logging_config import get_logger

logger = get_logger("app.errors")


def _error_response(status_code: int, code: str, message: str, details: dict | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details or {}}},
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            "app_error",
            extra={"path": request.url.path, "method": request.method, "status_code": exc.status_code},
        )
        return _error_response(exc.status_code, exc.error_code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "validation_error",
            "One or more fields failed validation.",
            {"errors": jsonable_encoder(exc.errors())},
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _error_response(exc.status_code, "http_error", str(exc.detail))

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
        logger.error("db_integrity_error", extra={"path": request.url.path})
        return _error_response(
            status.HTTP_409_CONFLICT, "conflict", "The record conflicts with existing data."
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_db_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        error_id = str(uuid.uuid4())
        logger.error("db_error", extra={"path": request.url.path}, exc_info=exc)
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "database_error",
            f"A database error occurred. Reference: {error_id}",
        )

    @app.exception_handler(Exception)
    async def handle_unhandled_error(request: Request, exc: Exception) -> JSONResponse:
        error_id = str(uuid.uuid4())
        logger.error("unhandled_error", extra={"path": request.url.path}, exc_info=exc)
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "internal_error",
            f"An unexpected error occurred. Reference: {error_id}",
        )

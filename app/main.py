"""FastAPI application entrypoint.

Run locally with:
    uvicorn app.main:app --reload --port 8000

Run in production with:
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
(see DEPLOYMENT.md for the recommended process manager / container setup)
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.error_handlers import register_exception_handlers
from app.core.logging_config import configure_logging, get_logger
from app.core.middleware import RequestLoggingMiddleware
from app.core.rate_limit import limiter
from app.core.security import warm_jwks_cache
from app.services.scheduler import start_scheduler, stop_scheduler

settings = get_settings()
configure_logging()
logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("app_starting", extra={"env": settings.APP_ENV})
    await warm_jwks_cache()
    start_scheduler()
    yield
    stop_scheduler()
    logger.info("app_stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description=(
            "Backend API for Gold Value Calculator — live gold rates, gold value "
            "& gold loan calculations, calculation history, and user settings."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request logging
    app.add_middleware(RequestLoggingMiddleware)

    # Centralized error handling
    register_exception_handlers(app)

    # Routes
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/health", tags=["Health"])
    async def health_check() -> dict:
        return {"status": "ok", "env": settings.APP_ENV}

    return app


app = create_app()

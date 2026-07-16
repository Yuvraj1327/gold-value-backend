"""Centralized application configuration.

All configuration is sourced from environment variables (`.env` locally,
real environment variables in production/CI). Nothing here is hardcoded —
see `.env.example` for the full list of required variables.
"""
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ------------------------------------------------------------------
    # App
    # ------------------------------------------------------------------
    APP_NAME: str = "Gold Value Calculator API"
    APP_ENV: str = Field(default="development")  # development | staging | production
    DEBUG: bool = Field(default=False)
    API_V1_PREFIX: str = "/api/v1"

    # ------------------------------------------------------------------
    # Database (Supabase Postgres connection string)
    # Format: postgresql+psycopg://postgres:[PASSWORD]@[HOST]:5432/postgres
    # ------------------------------------------------------------------
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # ------------------------------------------------------------------
    # Supabase
    # ------------------------------------------------------------------
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWT_SECRET: str

    # ------------------------------------------------------------------
    # JWT (for tokens minted directly by this backend, e.g. guest sessions)
    # ------------------------------------------------------------------
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    CORS_ORIGINS: str = "*"

    @field_validator("CORS_ORIGINS")
    @classmethod
    def _split_origins(cls, v: str) -> str:
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_CALCULATE: str = "30/minute"
    RATE_LIMIT_AUTH: str = "10/minute"

    # ------------------------------------------------------------------
    # Gold rate provider
    # ------------------------------------------------------------------
    GOLD_RATE_API_URL: str = "https://www.goldapi.io/api/XAU/INR"
    GOLD_RATE_API_KEY: str = ""
    GOLD_RATE_REFRESH_INTERVAL_MINUTES: int = 60
    GOLD_RATE_FALLBACK_24K: float = 7350.0  # INR per gram, used only if provider + DB both fail

    # Set to false in tests / one-off scripts to avoid starting the background
    # scheduler (and to avoid multiple AsyncIOScheduler instances competing
    # across repeated app startups within the same process).
    ENABLE_SCHEDULER: bool = True

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = True

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — read env vars once per process."""
    return Settings()

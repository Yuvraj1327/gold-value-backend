from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.core.config import get_settings
from app.core.exceptions import UpstreamServiceError
from app.core.logging_config import get_logger
from app.models.gold_rate import GoldRate
from app.repositories.gold_rate_repository import GoldRateRepository
from app.schemas.gold_rate import GoldRateResponse
from app.services.gold_rate_fetcher import fetch_live_rate
from app.utils.calculators import rate_for_purity

settings = get_settings()
logger = get_logger("app.gold_rate_service")


class GoldRateService:
    def __init__(self, repository: GoldRateRepository) -> None:
        self._repository = repository

    async def get_current_rate(self) -> GoldRateResponse:
        """Serves the latest DB row. If it's stale (older than the refresh
        interval) attempts one synchronous refresh; on any provider failure
        it falls back to the stale cached row rather than erroring out —
        satisfying "if offline / provider down, show cached value"."""
        latest = await self._repository.get_latest()

        if latest is None:
            # First-ever boot with an empty table: try a real fetch, but if
            # the provider is *also* unreachable at this exact moment, fall
            # back to the configured static rate rather than 502-ing every
            # caller until the provider happens to come back up.
            try:
                latest = await self.refresh_rate()
                return GoldRateResponse.model_validate(latest)
            except UpstreamServiceError:
                logger.warning("gold_rate_initial_fetch_failed_using_fallback")
                latest = await self._insert_fallback_snapshot()
                response = GoldRateResponse.model_validate(latest)
                response.is_stale = True
                return response

        is_stale = self._is_stale(latest.updated_at)
        if is_stale:
            try:
                latest = await self.refresh_rate()
            except UpstreamServiceError:
                logger.warning("gold_rate_refresh_failed_serving_cache")

        response = GoldRateResponse.model_validate(latest)
        response.is_stale = self._is_stale(latest.updated_at)
        return response

    async def refresh_rate(self) -> GoldRate:
        """Fetches a fresh rate from the provider and persists a new snapshot.

        Used both by the hourly APScheduler job and as a fallback inside
        `get_current_rate` when the cached value has expired.
        """
        fetched = await fetch_live_rate()
        snapshot = GoldRate(
            rate_24k=fetched.rate_24k,
            rate_22k=fetched.rate_22k,
            rate_20k=fetched.rate_20k,
            rate_18k=fetched.rate_18k,
            source=fetched.source,
        )
        return await self._repository.insert_snapshot(snapshot)

    async def _insert_fallback_snapshot(self) -> GoldRate:
        """Persists `settings.GOLD_RATE_FALLBACK_24K` as a snapshot so the
        app has *something* to serve — and so subsequent requests within
        the same outage read this same row instead of retrying the
        provider on every single request."""
        fallback_24k = settings.GOLD_RATE_FALLBACK_24K
        snapshot = GoldRate(
            rate_24k=fallback_24k,
            rate_22k=rate_for_purity(fallback_24k, 0.916),
            rate_20k=rate_for_purity(fallback_24k, 0.833),
            rate_18k=rate_for_purity(fallback_24k, 0.750),
            source="static_fallback",
        )
        return await self._repository.insert_snapshot(snapshot)

    @staticmethod
    def _is_stale(updated_at: datetime) -> bool:
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=UTC)
        ttl = timedelta(minutes=settings.GOLD_RATE_REFRESH_INTERVAL_MINUTES)
        return datetime.now(UTC) - updated_at > ttl

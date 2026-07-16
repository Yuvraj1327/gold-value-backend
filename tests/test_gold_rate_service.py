from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import get_settings
from app.core.exceptions import UpstreamServiceError
from app.models.gold_rate import GoldRate
from app.services.gold_rate_fetcher import FetchedRate
from app.services.gold_rate_service import GoldRateService

settings = get_settings()


class _FakeGoldRateRepository:
    def __init__(self, latest: GoldRate | None = None):
        self._latest = latest
        self.inserted: list[GoldRate] = []

    async def get_latest(self):
        return self._latest

    async def insert_snapshot(self, rate: GoldRate):
        rate.updated_at = datetime.now(UTC)
        self.inserted.append(rate)
        self._latest = rate
        return rate


def _make_rate(hours_old: float, rate_24k: float = 7000.0) -> GoldRate:
    return GoldRate(
        rate_24k=rate_24k,
        rate_22k=rate_24k * 0.916,
        rate_20k=rate_24k * 0.833,
        rate_18k=rate_24k * 0.75,
        source="test",
        updated_at=datetime.now(UTC) - timedelta(hours=hours_old),
    )


@pytest.mark.asyncio
async def test_serves_fresh_cached_rate_without_refetching():
    repo = _FakeGoldRateRepository(latest=_make_rate(hours_old=0.1))
    service = GoldRateService(repo)

    with patch("app.services.gold_rate_service.fetch_live_rate", new_callable=AsyncMock) as mocked_fetch:
        result = await service.get_current_rate()

    mocked_fetch.assert_not_called()
    assert result.is_stale is False
    assert result.rate_24k == 7000.0


@pytest.mark.asyncio
async def test_refreshes_when_stale():
    repo = _FakeGoldRateRepository(latest=_make_rate(hours_old=5))
    service = GoldRateService(repo)

    fresh = FetchedRate(
        rate_24k=7500.0, rate_22k=6870.0, rate_20k=6249.75, rate_18k=5625.0, source="provider"
    )
    with patch(
        "app.services.gold_rate_service.fetch_live_rate", new_callable=AsyncMock, return_value=fresh
    ) as mocked_fetch:
        result = await service.get_current_rate()

    mocked_fetch.assert_called_once()
    assert result.rate_24k == 7500.0
    assert result.is_stale is False


@pytest.mark.asyncio
async def test_falls_back_to_stale_cache_when_provider_fails():
    repo = _FakeGoldRateRepository(latest=_make_rate(hours_old=5, rate_24k=6800.0))
    service = GoldRateService(repo)

    with patch(
        "app.services.gold_rate_service.fetch_live_rate",
        new_callable=AsyncMock,
        side_effect=UpstreamServiceError("provider down"),
    ):
        result = await service.get_current_rate()

    # Falls back to the cached (still stale) value instead of raising.
    assert result.rate_24k == 6800.0
    assert result.is_stale is True


@pytest.mark.asyncio
async def test_uses_static_fallback_when_db_empty_and_provider_down():
    """Regression test for the bug where GOLD_RATE_FALLBACK_24K was
    defined in settings but never actually used anywhere — a fresh
    deployment with an empty gold_rates table AND an unreachable provider
    used to raise UpstreamServiceError (502) instead of degrading
    gracefully to the configured static rate."""
    repo = _FakeGoldRateRepository(latest=None)
    service = GoldRateService(repo)

    with patch(
        "app.services.gold_rate_service.fetch_live_rate",
        new_callable=AsyncMock,
        side_effect=UpstreamServiceError("provider down"),
    ):
        result = await service.get_current_rate()

    assert result.is_stale is True
    assert result.source == "static_fallback"
    assert result.rate_24k == settings.GOLD_RATE_FALLBACK_24K
    # A snapshot should have been persisted so subsequent requests don't
    # need to retry the (currently down) provider on every single call.
    assert len(repo.inserted) == 1

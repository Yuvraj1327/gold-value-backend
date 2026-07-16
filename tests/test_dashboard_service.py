from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import UpstreamServiceError
from app.models.calculation import Calculation
from app.models.gold_rate import GoldRate
from app.services.dashboard_service import DashboardService


class _FakeGoldRateRepo:
    def __init__(self, latest: GoldRate):
        self._latest = latest

    async def get_latest(self):
        return self._latest

    async def insert_snapshot(self, rate):
        self._latest = rate
        return rate


class _FakeCalculationRepo:
    def __init__(self, recent: list[Calculation], stats: tuple[int, float]):
        self._recent = recent
        self._stats = stats

    async def list_recent_for_user(self, user_id, limit):
        return self._recent[:limit]

    async def get_user_stats(self, user_id):
        return self._stats


def _fresh_rate() -> GoldRate:
    return GoldRate(
        rate_24k=7000.0,
        rate_22k=6412.0,
        rate_20k=5831.0,
        rate_18k=5250.0,
        source="test",
        updated_at=datetime.now(UTC),
    )


def _sample_calculation() -> Calculation:
    return Calculation(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        ornament_name="Ring",
        gross_weight=5.0,
        stone_weight=0.0,
        purity=0.916,
        gold_rate=7000.0,
        ltv_percent=75.0,
        wastage_percent=0.0,
        making_charges_percent=0.0,
        gst_percent=0.0,
        pure_gold_weight=4.58,
        gold_value=32060.0,
        making_charges_amount=0.0,
        gst_amount=0.0,
        final_value=32060.0,
        loan_amount=24045.0,
        created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_dashboard_summary_reports_live_status_for_fresh_rate():
    gold_rate_repo = _FakeGoldRateRepo(_fresh_rate())
    calc_repo = _FakeCalculationRepo(recent=[_sample_calculation()], stats=(3, 96180.0))
    service = DashboardService(gold_rate_repo, calc_repo)

    summary = await service.get_summary(uuid.uuid4())

    assert summary.market_status == "live"
    assert summary.stats.total_calculations == 3
    assert summary.stats.total_gold_value_calculated == 96180.0
    assert len(summary.recent_calculations) == 1


@pytest.mark.asyncio
async def test_dashboard_summary_reports_delayed_status_for_stale_rate():
    stale_rate = _fresh_rate()
    stale_rate.updated_at = datetime.now(UTC) - timedelta(hours=10)
    gold_rate_repo = _FakeGoldRateRepo(stale_rate)
    calc_repo = _FakeCalculationRepo(recent=[], stats=(0, 0.0))
    service = DashboardService(gold_rate_repo, calc_repo)

    with patch(
        "app.services.gold_rate_service.fetch_live_rate",
        new_callable=AsyncMock,
        side_effect=UpstreamServiceError("provider down"),
    ):
        summary = await service.get_summary(uuid.uuid4())

    assert summary.market_status == "delayed"
    assert summary.recent_calculations == []

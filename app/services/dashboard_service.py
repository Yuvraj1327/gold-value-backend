from __future__ import annotations

import uuid

from app.repositories.calculation_repository import CalculationRepository
from app.repositories.gold_rate_repository import GoldRateRepository
from app.schemas.calculation import CalculationResponse
from app.schemas.dashboard import DashboardResponse, DashboardStats
from app.services.gold_rate_service import GoldRateService

_RECENT_LIMIT = 5


class DashboardService:
    """Aggregates everything the Home/Dashboard screen needs into a single
    call (SOP requirement #5), instead of the client having to make 3+
    separate round trips.
    """

    def __init__(
        self,
        gold_rate_repository: GoldRateRepository,
        calculation_repository: CalculationRepository,
    ) -> None:
        self._gold_rate_service = GoldRateService(gold_rate_repository)
        self._calculation_repository = calculation_repository

    async def get_summary(self, user_id: uuid.UUID) -> DashboardResponse:
        gold_rate = await self._gold_rate_service.get_current_rate()

        recent = await self._calculation_repository.list_recent_for_user(user_id, limit=_RECENT_LIMIT)
        total_calculations, total_value = await self._calculation_repository.get_user_stats(user_id)

        return DashboardResponse(
            gold_rate=gold_rate,
            # A real "is the bullion market open right now" status would
            # require a market-hours calendar (which varies by exchange/
            # timezone and is out of scope here); "live" vs "delayed" is
            # the honest, directly-derivable signal we actually have —
            # whether the rate being served is fresh or a stale fallback.
            market_status="delayed" if gold_rate.is_stale else "live",
            recent_calculations=[CalculationResponse.model_validate(item) for item in recent],
            stats=DashboardStats(
                total_calculations=total_calculations,
                total_gold_value_calculated=total_value,
            ),
        )

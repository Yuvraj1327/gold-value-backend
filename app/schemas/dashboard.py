from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.schemas.calculation import CalculationResponse
from app.schemas.gold_rate import GoldRateResponse


class DashboardStats(BaseModel):
    total_calculations: int
    total_gold_value_calculated: float


class DashboardResponse(BaseModel):
    gold_rate: GoldRateResponse
    market_status: Literal["live", "delayed"]
    recent_calculations: list[CalculationResponse]
    stats: DashboardStats

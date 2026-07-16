from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GoldRateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rate_24k: float
    rate_22k: float
    rate_20k: float
    rate_18k: float
    source: str
    updated_at: datetime
    is_stale: bool = False

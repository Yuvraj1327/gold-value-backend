from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    default_ltv: float
    default_purity: str
    currency: str
    auto_rate: bool
    theme: Literal["light", "dark", "system"]
    default_wastage_percent: float
    default_making_charges_percent: float
    default_gst_percent: float
    notifications_enabled: bool


class UpdateSettingsRequest(BaseModel):
    default_ltv: float | None = Field(default=None, gt=0, le=100)
    default_purity: str | None = Field(default=None, pattern=r"^(18K|20K|22K|24K)$")
    currency: str | None = Field(default=None, min_length=3, max_length=10)
    auto_rate: bool | None = None
    theme: Literal["light", "dark", "system"] | None = None
    default_wastage_percent: float | None = Field(default=None, ge=0, le=100)
    default_making_charges_percent: float | None = Field(default=None, ge=0, le=100)
    default_gst_percent: float | None = Field(default=None, ge=0, le=100)
    notifications_enabled: bool | None = None

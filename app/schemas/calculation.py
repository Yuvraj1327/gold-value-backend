from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CalculateRequest(BaseModel):
    """Input for a stateless calculation preview (no persistence)."""

    gross_weight: float = Field(gt=0, le=100_000, description="Grams")
    stone_weight: float = Field(ge=0, le=100_000, default=0, description="Grams")
    purity: float = Field(gt=0, le=1, description="Fraction, e.g. 0.916 for 22K")
    gold_rate: float = Field(gt=0, description="Rate per gram for 24K gold, in the active currency")
    ltv_percent: float = Field(gt=0, le=100, default=75.0)

    wastage_percent: float = Field(
        ge=0, le=100, default=0, description="Extra chargeable weight % for crafting loss"
    )
    making_charges_percent: float = Field(
        ge=0, le=100, default=0, description="Jeweller labor charge, % of gold value"
    )
    gst_percent: float = Field(
        ge=0, le=100, default=0, description="GST %, applied to gold value + making charges"
    )

    @model_validator(mode="after")
    def validate_weights(self) -> CalculateRequest:
        if self.stone_weight > self.gross_weight:
            raise ValueError("Stone weight cannot exceed gross weight.")
        return self


class CalculateResponse(BaseModel):
    net_weight: float
    effective_weight: float
    pure_gold_weight: float
    gold_value: float
    making_charges_amount: float
    gst_amount: float
    final_value: float
    loan_amount: float


class SaveCalculationRequest(CalculateRequest):
    """Input for POST /history — same fields plus metadata to persist."""

    ornament_name: str = Field(min_length=1, max_length=255)
    # Serialised CertificateFormState — optional so older app versions that
    # don't yet send it still work without validation errors.
    certificate_snapshot: dict | None = None


class UpdateCalculationRequest(BaseModel):
    ornament_name: str | None = Field(default=None, min_length=1, max_length=255)
    gross_weight: float | None = Field(default=None, gt=0, le=100_000)
    stone_weight: float | None = Field(default=None, ge=0, le=100_000)
    purity: float | None = Field(default=None, gt=0, le=1)
    gold_rate: float | None = Field(default=None, gt=0)
    ltv_percent: float | None = Field(default=None, gt=0, le=100)
    wastage_percent: float | None = Field(default=None, ge=0, le=100)
    making_charges_percent: float | None = Field(default=None, ge=0, le=100)
    gst_percent: float | None = Field(default=None, ge=0, le=100)

    @model_validator(mode="after")
    def validate_weights(self) -> UpdateCalculationRequest:
        if (
            self.stone_weight is not None
            and self.gross_weight is not None
            and self.stone_weight > self.gross_weight
        ):
            raise ValueError("Stone weight cannot exceed gross weight.")
        return self


class CalculationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ornament_name: str
    gross_weight: float
    stone_weight: float
    purity: float
    gold_rate: float
    ltv_percent: float
    wastage_percent: float
    making_charges_percent: float
    gst_percent: float
    pure_gold_weight: float
    gold_value: float
    making_charges_amount: float
    gst_amount: float
    final_value: float
    loan_amount: float
    created_at: datetime
    certificate_snapshot: dict | None = None

    @field_validator("id", mode="before")
    @classmethod
    def _stringify_id(cls, value: object) -> str:
        """The ORM's `id` is a `uuid.UUID`; Pydantic v2 does not implicitly
        coerce UUID -> str even with `from_attributes=True`, so every
        history endpoint returning a real `Calculation` row would raise a
        500 without this. (Bug existed before this change ever added new
        fields — simply never caught by a test that used a real ORM
        instance until now.)"""
        return str(value)


class HistorySortBy(str, Enum):
    newest = "newest"
    oldest = "oldest"
    highest_value = "highest_value"
    lowest_value = "lowest_value"

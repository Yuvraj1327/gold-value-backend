from __future__ import annotations

import uuid

from pydantic import BaseModel, Field, model_validator


class LoanEstimateRequest(BaseModel):
    """Input for POST /loan/estimate.

    Either supply `gold_value` directly (e.g. from a `/calculate` preview
    that hasn't been saved yet), or `calculation_id` to base the estimate
    on an already-saved calculation's gold value — never both.
    """

    calculation_id: uuid.UUID | None = None
    gold_value: float | None = Field(default=None, gt=0)

    ltv_percent: float = Field(gt=0, le=100, default=75.0)
    annual_interest_rate_percent: float = Field(gt=0, le=100, default=12.0)
    tenure_months: int = Field(gt=0, le=360, default=12)

    @model_validator(mode="after")
    def validate_source(self) -> LoanEstimateRequest:
        if self.calculation_id is None and self.gold_value is None:
            raise ValueError("Provide either calculation_id or gold_value.")
        if self.calculation_id is not None and self.gold_value is not None:
            raise ValueError("Provide only one of calculation_id or gold_value, not both.")
        return self


class LoanEstimateResponse(BaseModel):
    gold_value: float
    eligible_loan_amount: float
    ltv_percent: float
    annual_interest_rate_percent: float
    tenure_months: int
    monthly_emi: float
    total_interest: float
    total_repayment: float

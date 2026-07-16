from __future__ import annotations

import uuid

from app.core.exceptions import ForbiddenError, NotFoundError, ValidationAppError
from app.repositories.calculation_repository import CalculationRepository
from app.schemas.loan import LoanEstimateRequest, LoanEstimateResponse
from app.utils.calculators import calculate_loan_amount
from app.utils.loan_calculator import LoanRepaymentSummary


class LoanService:
    """Gold Loan Estimator (SOP requirement #4): eligibility, LTV, EMI, and
    full repayment summary. Stateless — a saved `Calculation` only ever
    supplies the `gold_value` input here, never the loan terms themselves,
    since a user may want to preview several tenure/rate combinations
    against the same collateral without mutating their saved history.
    """

    def __init__(self, calculation_repository: CalculationRepository | None = None) -> None:
        self._calculation_repository = calculation_repository

    async def estimate(self, user_id: uuid.UUID, payload: LoanEstimateRequest) -> LoanEstimateResponse:
        gold_value = payload.gold_value

        if payload.calculation_id is not None:
            if self._calculation_repository is None:
                raise ValidationAppError("calculation_id lookup is not available in this context.")
            instance = await self._calculation_repository.get_by_id(payload.calculation_id)
            if instance is None:
                raise NotFoundError("Calculation not found.")
            if instance.user_id != user_id:
                raise ForbiddenError("You do not have access to this calculation.")
            gold_value = float(instance.gold_value)

        assert gold_value is not None  # guaranteed by LoanEstimateRequest's validator

        eligible_loan_amount = calculate_loan_amount(gold_value, payload.ltv_percent)

        summary = LoanRepaymentSummary(
            principal=eligible_loan_amount,
            annual_interest_rate_percent=payload.annual_interest_rate_percent,
            tenure_months=payload.tenure_months,
        )

        return LoanEstimateResponse(
            gold_value=gold_value,
            eligible_loan_amount=eligible_loan_amount,
            ltv_percent=payload.ltv_percent,
            annual_interest_rate_percent=payload.annual_interest_rate_percent,
            tenure_months=payload.tenure_months,
            monthly_emi=summary.monthly_emi,
            total_interest=summary.total_interest,
            total_repayment=summary.total_repayment,
        )

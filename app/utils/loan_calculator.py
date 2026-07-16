"""Gold loan EMI & repayment calculations.

Pure functions, `Decimal`-based, mirroring the style of `calculators.py`.
Uses the standard reducing-balance EMI formula used by virtually every
lender in India for gold loans.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def _to_decimal(value: float) -> Decimal:
    return Decimal(str(value))


def _round2(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def calculate_monthly_emi(
    principal: float,
    annual_interest_rate_percent: float,
    tenure_months: int,
) -> float:
    """EMI = P x r x (1+r)^n / ((1+r)^n - 1), where r is the *monthly*
    interest rate (annual rate / 12 / 100) and n is the tenure in months.

    Falls back to a simple principal/n split for a 0% interest rate (the
    standard formula divides by zero in that edge case).
    """
    if tenure_months <= 0:
        raise ValueError("tenure_months must be positive.")

    monthly_rate = _to_decimal(annual_interest_rate_percent) / Decimal("12") / Decimal("100")
    p = _to_decimal(principal)

    if monthly_rate == 0:
        return _round2(p / Decimal(tenure_months))

    factor = (Decimal("1") + monthly_rate) ** tenure_months
    emi = p * monthly_rate * factor / (factor - Decimal("1"))
    return _round2(emi)


class LoanRepaymentSummary:
    """Full repayment breakdown for a given principal/rate/tenure."""

    __slots__ = ("principal", "monthly_emi", "total_repayment", "total_interest", "tenure_months")

    def __init__(
        self,
        *,
        principal: float,
        annual_interest_rate_percent: float,
        tenure_months: int,
    ) -> None:
        self.principal = principal
        self.tenure_months = tenure_months
        self.monthly_emi = calculate_monthly_emi(principal, annual_interest_rate_percent, tenure_months)

        total_repayment = _to_decimal(self.monthly_emi) * Decimal(tenure_months)
        self.total_repayment = _round2(total_repayment)
        self.total_interest = _round2(total_repayment - _to_decimal(principal))

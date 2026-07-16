from __future__ import annotations

import pytest

from app.utils.loan_calculator import LoanRepaymentSummary, calculate_monthly_emi


def test_emi_standard_case():
    # Well-known reference case: 100000 principal, 12% annual, 12 months
    emi = calculate_monthly_emi(principal=100000, annual_interest_rate_percent=12.0, tenure_months=12)
    assert emi == pytest.approx(8884.88, abs=0.5)


def test_emi_zero_interest_splits_evenly():
    emi = calculate_monthly_emi(principal=12000, annual_interest_rate_percent=0.0, tenure_months=12)
    assert emi == 1000.0


def test_emi_rejects_non_positive_tenure():
    with pytest.raises(ValueError):
        calculate_monthly_emi(principal=10000, annual_interest_rate_percent=10.0, tenure_months=0)


def test_repayment_summary_totals_are_consistent():
    summary = LoanRepaymentSummary(principal=50000, annual_interest_rate_percent=10.0, tenure_months=6)
    assert summary.total_repayment == pytest.approx(summary.monthly_emi * 6, abs=0.01)
    assert summary.total_interest == pytest.approx(summary.total_repayment - 50000, abs=0.01)
    assert summary.total_interest > 0


def test_repayment_summary_zero_interest_has_no_interest():
    summary = LoanRepaymentSummary(principal=6000, annual_interest_rate_percent=0.0, tenure_months=6)
    assert summary.total_interest == 0.0
    assert summary.monthly_emi == 1000.0

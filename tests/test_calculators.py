from __future__ import annotations

import pytest

from app.utils.calculators import (
    CalculationBreakdown,
    calculate_effective_weight,
    calculate_gold_value,
    calculate_gst,
    calculate_loan_amount,
    calculate_making_charges,
    calculate_net_weight,
    calculate_pure_gold_weight,
    rate_for_purity,
)


def test_net_weight_subtracts_stone_from_gross():
    assert calculate_net_weight(gross_weight=10.5, stone_weight=1.5) == 9.0


def test_net_weight_handles_decimals_precisely():
    # Classic float trap: 10.1 - 0.1 must be exactly 10.0, not 9.999999999999998
    assert calculate_net_weight(gross_weight=10.1, stone_weight=0.1) == 10.0


def test_pure_gold_weight_applies_purity_fraction():
    # 22K purity = 0.916
    assert calculate_pure_gold_weight(net_weight=10.0, purity=0.916) == 9.16


def test_gold_value_multiplies_by_rate():
    assert calculate_gold_value(pure_gold_weight=9.16, gold_rate=6000) == 54960.0


def test_loan_amount_applies_ltv_percent():
    assert calculate_loan_amount(gold_value=54960.0, ltv_percent=75.0) == 41220.0


def test_rate_for_purity_derives_22k_from_24k():
    assert rate_for_purity(rate_24k=7350.0, purity=0.916) == pytest.approx(6732.6, abs=0.01)


def test_calculation_breakdown_end_to_end():
    breakdown = CalculationBreakdown(
        gross_weight=20.0,
        stone_weight=2.0,
        purity=0.916,
        gold_rate=6000.0,
        ltv_percent=75.0,
    )
    assert breakdown.net_weight == 18.0
    assert breakdown.pure_gold_weight == pytest.approx(16.488, abs=0.001)
    assert breakdown.gold_value == pytest.approx(98928.0, abs=0.01)
    assert breakdown.loan_amount == pytest.approx(74196.0, abs=0.01)


def test_effective_weight_applies_wastage():
    # 18g net weight + 2% wastage = 18.36g effective weight
    assert calculate_effective_weight(net_weight=18.0, wastage_percent=2.0) == pytest.approx(18.36, abs=0.001)


def test_effective_weight_zero_wastage_equals_net_weight():
    assert calculate_effective_weight(net_weight=18.0, wastage_percent=0.0) == 18.0


def test_making_charges_percent_of_gold_value():
    assert calculate_making_charges(gold_value=100000.0, making_charges_percent=8.0) == 8000.0


def test_gst_applies_to_subtotal_including_making_charges():
    # GST is charged on (gold value + making charges), not gold value alone
    assert calculate_gst(subtotal=108000.0, gst_percent=3.0) == pytest.approx(3240.0, abs=0.01)


def test_breakdown_with_wastage_making_charges_and_gst():
    breakdown = CalculationBreakdown(
        gross_weight=20.0,
        stone_weight=2.0,
        purity=0.916,
        gold_rate=6000.0,
        ltv_percent=75.0,
        wastage_percent=2.0,
        making_charges_percent=8.0,
        gst_percent=3.0,
    )
    # effective_weight = 18 * 1.02 = 18.36
    assert breakdown.effective_weight == pytest.approx(18.36, abs=0.001)
    # pure_gold_weight = 18.36 * 0.916
    assert breakdown.pure_gold_weight == pytest.approx(16.82, abs=0.01)
    # gold_value = pure_gold_weight * 6000 (each step rounded, per CalculationBreakdown's rounding rules)
    assert breakdown.gold_value == pytest.approx(100908.0, abs=1.0)
    # making_charges = gold_value * 8%
    assert breakdown.making_charges_amount == pytest.approx(breakdown.gold_value * 0.08, abs=0.01)
    # gst = (gold_value + making_charges) * 3%
    subtotal = breakdown.gold_value + breakdown.making_charges_amount
    assert breakdown.gst_amount == pytest.approx(subtotal * 0.03, abs=0.01)
    # final_value = subtotal + gst
    assert breakdown.final_value == pytest.approx(subtotal + breakdown.gst_amount, abs=0.01)


def test_loan_amount_is_based_on_gold_value_not_final_value():
    """Regression guard: a gold loan is collateralized against the metal
    only — making charges and GST must never inflate the loan basis, even
    when they're non-zero."""
    breakdown = CalculationBreakdown(
        gross_weight=20.0,
        stone_weight=2.0,
        purity=0.916,
        gold_rate=6000.0,
        ltv_percent=75.0,
        wastage_percent=2.0,
        making_charges_percent=8.0,
        gst_percent=3.0,
    )
    assert breakdown.final_value > breakdown.gold_value
    assert breakdown.loan_amount == pytest.approx(breakdown.gold_value * 0.75, abs=0.01)
    assert breakdown.loan_amount != pytest.approx(breakdown.final_value * 0.75, abs=0.01)

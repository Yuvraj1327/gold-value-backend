"""Gold value & loan calculation formulas.

Kept as pure functions (no I/O, no DB) so they're trivially unit-testable
and reusable from both the `/calculate` preview endpoint and the
`/history` persistence flow. Uses `Decimal` throughout to avoid binary
floating-point rounding errors in money calculations.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def _to_decimal(value: float) -> Decimal:
    return Decimal(str(value))


def _round2(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _round3(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))


def calculate_net_weight(gross_weight: float, stone_weight: float) -> float:
    """Net Weight = Gross Weight - Stone Weight."""
    result = _to_decimal(gross_weight) - _to_decimal(stone_weight)
    return _round3(result)


def calculate_pure_gold_weight(net_weight: float, purity: float) -> float:
    """Pure Gold Weight = Net Weight × Purity %."""
    result = _to_decimal(net_weight) * _to_decimal(purity)
    return _round3(result)


def calculate_gold_value(pure_gold_weight: float, gold_rate: float) -> float:
    """Gold Value = Pure Gold Weight × Gold Rate (rate per gram of pure/24K gold)."""
    result = _to_decimal(pure_gold_weight) * _to_decimal(gold_rate)
    return _round2(result)


def calculate_loan_amount(gold_value: float, ltv_percent: float) -> float:
    """Loan Amount = Gold Value × LTV %."""
    result = _to_decimal(gold_value) * (_to_decimal(ltv_percent) / Decimal("100"))
    return _round2(result)


def rate_for_purity(rate_24k: float, purity: float) -> float:
    """Derives the effective per-gram rate for a given purity from the 24K rate.

    Used when the caller supplies a raw 24K market rate and we need the
    equivalent 18K/20K/22K rate for display (Home screen rate cards).
    """
    result = _to_decimal(rate_24k) * _to_decimal(purity)
    return _round2(result)


def calculate_effective_weight(net_weight: float, wastage_percent: float) -> float:
    """Effective Weight = Net Weight × (1 + Wastage % / 100).

    Wastage accounts for metal lost during crafting (polishing, stone
    setting, etc.) that jewellers pass on to the customer as extra
    chargeable weight — a standard, real-world jewellery pricing practice,
    distinct from the stone deduction already applied to get net weight.
    """
    result = _to_decimal(net_weight) * (Decimal("1") + _to_decimal(wastage_percent) / Decimal("100"))
    return _round3(result)


def calculate_making_charges(gold_value: float, making_charges_percent: float) -> float:
    """Making Charges = Gold Value × Making Charges % — the jeweller's
    labor/craftsmanship fee, charged on top of the raw metal value."""
    result = _to_decimal(gold_value) * (_to_decimal(making_charges_percent) / Decimal("100"))
    return _round2(result)


def calculate_gst(subtotal: float, gst_percent: float) -> float:
    """GST = (Gold Value + Making Charges) × GST % — applied to the full
    pre-tax invoice subtotal, matching how GST is charged on gold jewellery
    in practice (metal value + making charges, not on metal value alone)."""
    result = _to_decimal(subtotal) * (_to_decimal(gst_percent) / Decimal("100"))
    return _round2(result)


class CalculationBreakdown:
    """Value object bundling every intermediate + final figure for a calculation.

    `loan_amount` is deliberately based on `gold_value` (raw metal value)
    only — never on `final_value` — because a gold loan is collateralized
    against the metal itself; making charges and GST reflect retail pricing
    and have no resale/melt value, so lenders never include them in LTV
    calculations. This matches real-world gold loan practice.
    """

    __slots__ = (
        "net_weight",
        "effective_weight",
        "pure_gold_weight",
        "gold_value",
        "making_charges_amount",
        "gst_amount",
        "final_value",
        "loan_amount",
    )

    def __init__(
        self,
        *,
        gross_weight: float,
        stone_weight: float,
        purity: float,
        gold_rate: float,
        ltv_percent: float,
        wastage_percent: float = 0.0,
        making_charges_percent: float = 0.0,
        gst_percent: float = 0.0,
    ) -> None:
        self.net_weight = calculate_net_weight(gross_weight, stone_weight)
        self.effective_weight = calculate_effective_weight(self.net_weight, wastage_percent)
        self.pure_gold_weight = calculate_pure_gold_weight(self.effective_weight, purity)
        self.gold_value = calculate_gold_value(self.pure_gold_weight, gold_rate)
        self.loan_amount = calculate_loan_amount(self.gold_value, ltv_percent)

        self.making_charges_amount = calculate_making_charges(self.gold_value, making_charges_percent)
        pre_tax_subtotal = _to_decimal(self.gold_value) + _to_decimal(self.making_charges_amount)
        self.gst_amount = calculate_gst(float(pre_tax_subtotal), gst_percent)
        self.final_value = _round2(pre_tax_subtotal + _to_decimal(self.gst_amount))

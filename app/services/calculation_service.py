from __future__ import annotations

from app.schemas.calculation import CalculateRequest, CalculateResponse
from app.utils.calculators import CalculationBreakdown


class CalculationService:
    """Pure orchestration around `CalculationBreakdown` — no persistence.

    Kept separate from `HistoryService` (which saves calculations) because
    the Flutter app calls `/calculate` on every keystroke-debounced form
    change for instant live results, and that should never touch the DB.
    """

    def calculate(self, payload: CalculateRequest) -> CalculateResponse:
        breakdown = CalculationBreakdown(
            gross_weight=payload.gross_weight,
            stone_weight=payload.stone_weight,
            purity=payload.purity,
            gold_rate=payload.gold_rate,
            ltv_percent=payload.ltv_percent,
            wastage_percent=payload.wastage_percent,
            making_charges_percent=payload.making_charges_percent,
            gst_percent=payload.gst_percent,
        )
        return CalculateResponse(
            net_weight=breakdown.net_weight,
            effective_weight=breakdown.effective_weight,
            pure_gold_weight=breakdown.pure_gold_weight,
            gold_value=breakdown.gold_value,
            making_charges_amount=breakdown.making_charges_amount,
            gst_amount=breakdown.gst_amount,
            final_value=breakdown.final_value,
            loan_amount=breakdown.loan_amount,
        )

from __future__ import annotations

import uuid
from datetime import datetime

from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.calculation import Calculation
from app.repositories.calculation_repository import CalculationRepository
from app.schemas.calculation import (
    HistorySortBy,
    SaveCalculationRequest,
    UpdateCalculationRequest,
)
from app.schemas.common import PaginatedResponse
from app.utils.calculators import CalculationBreakdown
from app.utils.pagination import PageRequest


class HistoryService:
    def __init__(self, repository: CalculationRepository) -> None:
        self._repository = repository

    async def save(self, user_id: uuid.UUID, payload: SaveCalculationRequest) -> Calculation:
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
        instance = Calculation(
            user_id=user_id,
            ornament_name=payload.ornament_name,
            gross_weight=payload.gross_weight,
            stone_weight=payload.stone_weight,
            purity=payload.purity,
            gold_rate=payload.gold_rate,
            ltv_percent=payload.ltv_percent,
            wastage_percent=payload.wastage_percent,
            making_charges_percent=payload.making_charges_percent,
            gst_percent=payload.gst_percent,
            pure_gold_weight=breakdown.pure_gold_weight,
            gold_value=breakdown.gold_value,
            making_charges_amount=breakdown.making_charges_amount,
            gst_amount=breakdown.gst_amount,
            final_value=breakdown.final_value,
            loan_amount=breakdown.loan_amount,
            certificate_snapshot=payload.certificate_snapshot,
        )
        return await self._repository.add(instance)

    async def list_paginated(
        self,
        user_id: uuid.UUID,
        *,
        page: int,
        page_size: int,
        search: str | None,
        sort_by: HistorySortBy,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> PaginatedResponse:
        page_request = PageRequest(page=page, page_size=page_size)
        items, total = await self._repository.list_for_user(
            user_id,
            page_request=page_request,
            search=search,
            sort_by=sort_by,
            date_from=date_from,
            date_to=date_to,
        )
        has_next = page_request.offset + len(items) < total
        return PaginatedResponse(
            items=items,
            total=total,
            page=page_request.page,
            page_size=page_request.page_size,
            has_next=has_next,
        )

    async def export_csv(
        self,
        user_id: uuid.UUID,
        *,
        search: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> str:
        """Builds a CSV export of the user's history (SOP §7 "Export
        support"). Uses the stdlib `csv` module rather than hand-joining
        strings, so ornament names containing commas/quotes are escaped
        correctly."""
        import csv
        import io

        items = await self._repository.list_for_export(
            user_id, search=search, date_from=date_from, date_to=date_to
        )

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "Ornament Name",
                "Gross Weight (g)",
                "Stone Weight (g)",
                "Purity",
                "Gold Rate",
                "Wastage %",
                "Making Charges %",
                "GST %",
                "Pure Gold Weight (g)",
                "Gold Value",
                "Making Charges Amount",
                "GST Amount",
                "Final Value",
                "LTV %",
                "Loan Amount",
                "Created At",
            ]
        )
        for item in items:
            writer.writerow(
                [
                    item.ornament_name,
                    item.gross_weight,
                    item.stone_weight,
                    item.purity,
                    item.gold_rate,
                    item.wastage_percent,
                    item.making_charges_percent,
                    item.gst_percent,
                    item.pure_gold_weight,
                    item.gold_value,
                    item.making_charges_amount,
                    item.gst_amount,
                    item.final_value,
                    item.ltv_percent,
                    item.loan_amount,
                    item.created_at.isoformat(),
                ]
            )
        return buffer.getvalue()

    async def update(
        self, user_id: uuid.UUID, calculation_id: uuid.UUID, payload: UpdateCalculationRequest
    ) -> Calculation:
        instance = await self._get_owned(user_id, calculation_id)

        updates = payload.model_dump(exclude_unset=True)
        direct_fields = (
            "ornament_name",
            "gross_weight",
            "stone_weight",
            "purity",
            "gold_rate",
            "ltv_percent",
            "wastage_percent",
            "making_charges_percent",
            "gst_percent",
        )
        for field in direct_fields:
            if field in updates:
                setattr(instance, field, updates[field])

        # Recompute derived figures if any input to the formula changed.
        # Bug fix: previously this defaulted a missing `ltv_percent` (and
        # any other omitted charge field) to a hardcoded value rather than
        # the record's own already-persisted one — which silently reset,
        # e.g., a saved calculation's LTV to 75% whenever only its weight
        # was edited. Reading from `instance` (already updated above)
        # instead of `updates` fixes this for every recomputed field.
        recompute_fields = {
            "gross_weight",
            "stone_weight",
            "purity",
            "gold_rate",
            "ltv_percent",
            "wastage_percent",
            "making_charges_percent",
            "gst_percent",
        }
        if recompute_fields & updates.keys():
            breakdown = CalculationBreakdown(
                gross_weight=float(instance.gross_weight),
                stone_weight=float(instance.stone_weight),
                purity=float(instance.purity),
                gold_rate=float(instance.gold_rate),
                ltv_percent=float(instance.ltv_percent),
                wastage_percent=float(instance.wastage_percent),
                making_charges_percent=float(instance.making_charges_percent),
                gst_percent=float(instance.gst_percent),
            )
            instance.pure_gold_weight = breakdown.pure_gold_weight
            instance.gold_value = breakdown.gold_value
            instance.making_charges_amount = breakdown.making_charges_amount
            instance.gst_amount = breakdown.gst_amount
            instance.final_value = breakdown.final_value
            instance.loan_amount = breakdown.loan_amount

        self._repository.session.add(instance)
        await self._repository.session.commit()
        await self._repository.session.refresh(instance)
        return instance

    async def delete(self, user_id: uuid.UUID, calculation_id: uuid.UUID) -> None:
        instance = await self._get_owned(user_id, calculation_id)
        await self._repository.delete(instance)

    async def _get_owned(self, user_id: uuid.UUID, calculation_id: uuid.UUID) -> Calculation:
        instance = await self._repository.get_by_id(calculation_id)
        if instance is None:
            raise NotFoundError("Calculation not found.")
        if instance.user_id != user_id:
            raise ForbiddenError("You do not have access to this calculation.")
        return instance

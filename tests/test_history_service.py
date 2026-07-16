from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.models.calculation import Calculation
from app.schemas.calculation import UpdateCalculationRequest
from app.services.history_service import HistoryService


class _FakeCalculationRepository:
    """Minimal in-memory stand-in for `CalculationRepository`, mirroring
    the style of `_FakeGoldRateRepository` in test_gold_rate_service.py —
    lets us exercise `HistoryService`'s business logic (including the
    recompute-on-update path) without a real database."""

    def __init__(self) -> None:
        self.session = self  # HistoryService.update() calls self._repository.session.add/commit/refresh
        self._store: dict[uuid.UUID, Calculation] = {}

    def add(self, instance):
        self._store[instance.id] = instance

    async def commit(self):
        pass

    async def refresh(self, instance):
        pass

    async def get_by_id(self, id_value: uuid.UUID):
        return self._store.get(id_value)

    async def delete(self, instance):
        self._store.pop(instance.id, None)


def _make_saved_calculation(*, ltv_percent: float = 60.0) -> Calculation:
    return Calculation(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        ornament_name="Test Bangle",
        gross_weight=20.0,
        stone_weight=2.0,
        purity=0.916,
        gold_rate=6000.0,
        ltv_percent=ltv_percent,
        wastage_percent=0.0,
        making_charges_percent=0.0,
        gst_percent=0.0,
        pure_gold_weight=16.488,
        gold_value=98928.0,
        making_charges_amount=0.0,
        gst_amount=0.0,
        final_value=98928.0,
        loan_amount=98928.0 * ltv_percent / 100,
        created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_update_preserves_ltv_percent_when_not_supplied():
    """Regression test for the bug where updating any other field (e.g.
    gross_weight) on a saved calculation silently reset its loan basis to
    a hardcoded 75%, because ltv_percent was never persisted and the old
    code defaulted to 75.0 whenever the update payload didn't include it.
    """
    repo = _FakeCalculationRepository()
    saved = _make_saved_calculation(ltv_percent=60.0)
    repo._store[saved.id] = saved

    service = HistoryService(repo)
    updated = await service.update(
        saved.user_id,
        saved.id,
        UpdateCalculationRequest(gross_weight=25.0),
    )

    assert float(updated.ltv_percent) == 60.0
    expected_loan_amount = float(updated.gold_value) * 0.60
    assert float(updated.loan_amount) == pytest.approx(expected_loan_amount, abs=0.01)


@pytest.mark.asyncio
async def test_update_applies_new_ltv_percent_when_supplied():
    repo = _FakeCalculationRepository()
    saved = _make_saved_calculation(ltv_percent=60.0)
    repo._store[saved.id] = saved

    service = HistoryService(repo)
    updated = await service.update(
        saved.user_id,
        saved.id,
        UpdateCalculationRequest(ltv_percent=80.0),
    )

    assert float(updated.ltv_percent) == 80.0
    expected_loan_amount = float(updated.gold_value) * 0.80
    assert float(updated.loan_amount) == pytest.approx(expected_loan_amount, abs=0.01)


@pytest.mark.asyncio
async def test_update_recomputes_charges_when_making_charges_changes():
    repo = _FakeCalculationRepository()
    saved = _make_saved_calculation(ltv_percent=75.0)
    repo._store[saved.id] = saved

    service = HistoryService(repo)
    updated = await service.update(
        saved.user_id,
        saved.id,
        UpdateCalculationRequest(making_charges_percent=10.0),
    )

    assert float(updated.making_charges_percent) == 10.0
    assert float(updated.making_charges_amount) == pytest.approx(float(updated.gold_value) * 0.10, abs=0.01)
    assert float(updated.final_value) > float(updated.gold_value)

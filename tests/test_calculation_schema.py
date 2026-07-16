from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.calculation import CalculateRequest


def test_valid_request_passes():
    req = CalculateRequest(gross_weight=10, stone_weight=1, purity=0.916, gold_rate=6000, ltv_percent=75)
    assert req.gross_weight == 10


def test_stone_weight_exceeding_gross_weight_is_rejected():
    with pytest.raises(ValidationError, match="Stone weight cannot exceed gross weight"):
        CalculateRequest(gross_weight=5, stone_weight=10, purity=0.916, gold_rate=6000)


def test_negative_gross_weight_is_rejected():
    with pytest.raises(ValidationError):
        CalculateRequest(gross_weight=-1, stone_weight=0, purity=0.916, gold_rate=6000)


def test_negative_stone_weight_is_rejected():
    with pytest.raises(ValidationError):
        CalculateRequest(gross_weight=10, stone_weight=-1, purity=0.916, gold_rate=6000)


def test_purity_out_of_range_is_rejected():
    with pytest.raises(ValidationError):
        CalculateRequest(gross_weight=10, stone_weight=0, purity=1.5, gold_rate=6000)


def test_zero_gold_rate_is_rejected():
    with pytest.raises(ValidationError):
        CalculateRequest(gross_weight=10, stone_weight=0, purity=0.916, gold_rate=0)


def test_default_ltv_percent_is_75():
    req = CalculateRequest(gross_weight=10, stone_weight=0, purity=0.916, gold_rate=6000)
    assert req.ltv_percent == 75.0

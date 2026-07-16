from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.core.config import get_settings

settings = get_settings()


def test_loan_estimate_with_gold_value(client: TestClient):
    response = client.post(
        f"{settings.API_V1_PREFIX}/loan/estimate",
        json={
            "gold_value": 100000,
            "ltv_percent": 75,
            "annual_interest_rate_percent": 12,
            "tenure_months": 12,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["eligible_loan_amount"] == 75000.0
    assert body["monthly_emi"] == 6663.66
    assert body["total_repayment"] > body["eligible_loan_amount"]
    assert body["total_interest"] > 0


def test_loan_estimate_rejects_both_sources(client: TestClient):
    response = client.post(
        f"{settings.API_V1_PREFIX}/loan/estimate",
        json={
            "gold_value": 100000,
            "calculation_id": str(uuid.uuid4()),
            "ltv_percent": 75,
        },
    )
    assert response.status_code == 422


def test_loan_estimate_rejects_neither_source(client: TestClient):
    response = client.post(
        f"{settings.API_V1_PREFIX}/loan/estimate",
        json={"ltv_percent": 75},
    )
    assert response.status_code == 422


def test_loan_estimate_requires_auth():
    from app.main import app

    with TestClient(app) as unauthenticated_client:
        response = unauthenticated_client.post(
            f"{settings.API_V1_PREFIX}/loan/estimate",
            json={"gold_value": 100000},
        )
    assert response.status_code == 401

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import get_settings

settings = get_settings()


def test_calculate_endpoint_returns_breakdown(client: TestClient):
    response = client.post(
        f"{settings.API_V1_PREFIX}/calculate",
        json={
            "gross_weight": 20,
            "stone_weight": 2,
            "purity": 0.916,
            "gold_rate": 6000,
            "ltv_percent": 75,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["net_weight"] == 18.0
    assert body["pure_gold_weight"] == 16.488
    assert body["gold_value"] == 98928.0
    assert body["loan_amount"] == 74196.0


def test_calculate_endpoint_rejects_invalid_stone_weight(client: TestClient):
    response = client.post(
        f"{settings.API_V1_PREFIX}/calculate",
        json={"gross_weight": 5, "stone_weight": 10, "purity": 0.916, "gold_rate": 6000},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"


def test_calculate_endpoint_requires_auth():
    from app.main import app

    with TestClient(app) as unauthenticated_client:
        response = unauthenticated_client.post(
            f"{settings.API_V1_PREFIX}/calculate",
            json={"gross_weight": 10, "stone_weight": 0, "purity": 0.916, "gold_rate": 6000},
        )
    assert response.status_code == 401

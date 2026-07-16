"""Fetches the live 24K gold rate from an external provider.

Written against the goldapi.io response contract (`price_gram_24k`,
`price_gram_22k`, etc. in the response body), which is a common shape
among gold-price APIs. If a different provider is used, only this file
needs to change — `GoldRateService` only depends on `fetch_live_rate()`'s
return contract, not on any provider-specific fields.
"""
from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.core.exceptions import UpstreamServiceError
from app.core.logging_config import get_logger
from app.utils.calculators import rate_for_purity

settings = get_settings()
logger = get_logger("app.gold_rate_fetcher")


class FetchedRate:
    __slots__ = ("rate_24k", "rate_22k", "rate_20k", "rate_18k", "source")

    def __init__(
        self,
        *,
        rate_24k: float,
        rate_22k: float,
        rate_20k: float,
        rate_18k: float,
        source: str,
    ) -> None:
        self.rate_24k = rate_24k
        self.rate_22k = rate_22k
        self.rate_20k = rate_20k
        self.rate_18k = rate_18k
        self.source = source


async def fetch_live_rate() -> FetchedRate:
    """Calls the configured provider. Raises UpstreamServiceError on any failure."""
    if not settings.GOLD_RATE_API_KEY:
        raise UpstreamServiceError("Gold rate provider API key is not configured.")

    headers = {"x-access-token": settings.GOLD_RATE_API_KEY, "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(settings.GOLD_RATE_API_URL, headers=headers)
    except httpx.HTTPError as exc:
        logger.error("gold_rate_provider_network_error")
        raise UpstreamServiceError("Could not reach the gold rate provider.") from exc

    if response.status_code != 200:
        raise UpstreamServiceError(f"Gold rate provider returned status {response.status_code}.")

    data = response.json()

    rate_24k = data.get("price_gram_24k")
    if rate_24k is None:
        # Fall back to per-ounce price if the provider only returns that.
        price_per_ounce = data.get("price")
        if price_per_ounce is None:
            raise UpstreamServiceError("Gold rate provider response missing price data.")
        rate_24k = float(price_per_ounce) / 31.1035  # troy ounce -> gram

    rate_24k = float(rate_24k)
    rate_22k = (
        float(data["price_gram_22k"]) if data.get("price_gram_22k") else rate_for_purity(rate_24k, 0.916)
    )
    rate_20k = (
        float(data["price_gram_20k"]) if data.get("price_gram_20k") else rate_for_purity(rate_24k, 0.833)
    )
    rate_18k = (
        float(data["price_gram_18k"]) if data.get("price_gram_18k") else rate_for_purity(rate_24k, 0.750)
    )

    return FetchedRate(
        rate_24k=rate_24k,
        rate_22k=rate_22k,
        rate_20k=rate_20k,
        rate_18k=rate_18k,
        source=data.get("metal", "goldapi") if isinstance(data.get("metal"), str) else "goldapi",
    )

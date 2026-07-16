from fastapi import APIRouter, Depends, Request

from app.api.deps import get_gold_rate_service
from app.core.rate_limit import limiter
from app.core.security import CurrentUser, get_optional_user
from app.schemas.gold_rate import GoldRateResponse
from app.services.gold_rate_service import GoldRateService

router = APIRouter(prefix="/gold-rate", tags=["Gold Rate"])


@router.get("", response_model=GoldRateResponse)
@limiter.limit("60/minute")
async def get_gold_rate(
    request: Request,
    _user: CurrentUser | None = Depends(get_optional_user),
    service: GoldRateService = Depends(get_gold_rate_service),
) -> GoldRateResponse:
    """Returns the latest cached gold rate, refreshing it if stale.

    Available to signed-out callers too (gold rates aren't sensitive), but
    still resolves the caller's identity if a token is present for future
    personalization (e.g. per-user preferred purity default).
    """
    return await service.get_current_rate()

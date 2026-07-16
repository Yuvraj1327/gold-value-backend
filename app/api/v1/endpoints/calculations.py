from fastapi import APIRouter, Depends, Request

from app.api.deps import get_calculation_service
from app.core.rate_limit import limiter
from app.core.security import CurrentUser, get_current_user
from app.schemas.calculation import CalculateRequest, CalculateResponse
from app.services.calculation_service import CalculationService

router = APIRouter(tags=["Calculator"])


@router.post("/calculate", response_model=CalculateResponse)
@limiter.limit("30/minute")
async def calculate(
    request: Request,
    payload: CalculateRequest,
    _user: CurrentUser = Depends(get_current_user),
    service: CalculationService = Depends(get_calculation_service),
) -> CalculateResponse:
    """Stateless calculation preview — does not persist anything.

    Requires authentication (guest sessions included) purely to keep the
    rate limit meaningful per-caller rather than opening it fully anonymous;
    it never reads or writes any user-scoped data.
    """
    return service.calculate(payload)

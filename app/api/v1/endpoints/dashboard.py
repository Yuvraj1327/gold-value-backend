import uuid

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_dashboard_service
from app.core.rate_limit import limiter
from app.core.security import CurrentUser, get_current_user
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardResponse)
@limiter.limit("60/minute")
async def get_dashboard_summary(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service),
) -> DashboardResponse:
    """Dashboard APIs (SOP requirement #5): live gold rate, market status,
    this user's recent calculations, and their aggregate stats — all in
    one call.
    """
    return await service.get_summary(uuid.UUID(user.id))

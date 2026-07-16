import uuid

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_admin_service, get_current_admin, get_gold_rate_service
from app.core.rate_limit import limiter
from app.core.security import CurrentUser
from app.schemas.admin import AdminStatsResponse, UpdateUserRoleRequest, UserRoleResponse
from app.schemas.gold_rate import GoldRateResponse
from app.services.admin_service import AdminService
from app.services.gold_rate_service import GoldRateService

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/stats", response_model=AdminStatsResponse)
@limiter.limit("30/minute")
async def get_platform_stats(
    request: Request,
    _admin: CurrentUser = Depends(get_current_admin),
    service: AdminService = Depends(get_admin_service),
) -> AdminStatsResponse:
    """Role-based authorization in action: only callers whose `users.role`
    is `"admin"` can reach this — everyone else gets a 403 `forbidden`."""
    return await service.get_platform_stats()


@router.put("/users/{user_id}/role", response_model=UserRoleResponse)
@limiter.limit("10/minute")
async def update_user_role(
    request: Request,
    user_id: uuid.UUID,
    payload: UpdateUserRoleRequest,
    _admin: CurrentUser = Depends(get_current_admin),
    service: AdminService = Depends(get_admin_service),
) -> UserRoleResponse:
    """Promotes/demotes another user's role. Admin-only — this is the only
    way a user ever becomes an admin via the API (there is deliberately no
    self-service "become admin" endpoint)."""
    return await service.update_user_role(user_id, payload.role)


@router.post("/gold-rate/refresh", response_model=GoldRateResponse)
@limiter.limit("10/minute")
async def force_refresh_gold_rate(
    request: Request,
    _admin: CurrentUser = Depends(get_current_admin),
    service: GoldRateService = Depends(get_gold_rate_service),
) -> GoldRateResponse:
    """Manually triggers an immediate gold-rate refresh from the live
    provider, bypassing the hourly scheduler — useful for admins after a
    known provider outage instead of waiting out the refresh interval."""
    snapshot = await service.refresh_rate()
    return GoldRateResponse.model_validate(snapshot)

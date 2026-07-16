import uuid

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_settings_service
from app.core.rate_limit import limiter
from app.core.security import CurrentUser, get_current_user
from app.schemas.settings import SettingsResponse, UpdateSettingsRequest
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("", response_model=SettingsResponse)
@limiter.limit("60/minute")
async def get_settings_endpoint(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    service: SettingsService = Depends(get_settings_service),
) -> SettingsResponse:
    instance = await service.get(uuid.UUID(user.id))
    return SettingsResponse.model_validate(instance)


@router.put("", response_model=SettingsResponse)
@limiter.limit("30/minute")
async def update_settings_endpoint(
    request: Request,
    payload: UpdateSettingsRequest,
    user: CurrentUser = Depends(get_current_user),
    service: SettingsService = Depends(get_settings_service),
) -> SettingsResponse:
    instance = await service.update(uuid.UUID(user.id), payload)
    return SettingsResponse.model_validate(instance)

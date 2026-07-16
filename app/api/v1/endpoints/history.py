import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from app.api.deps import get_history_service
from app.core.rate_limit import limiter
from app.core.security import CurrentUser, get_current_user
from app.schemas.calculation import (
    CalculationResponse,
    HistorySortBy,
    SaveCalculationRequest,
    UpdateCalculationRequest,
)
from app.schemas.common import PaginatedResponse
from app.services.history_service import HistoryService

router = APIRouter(prefix="/history", tags=["History"])


@router.get("", response_model=PaginatedResponse[CalculationResponse])
@limiter.limit("60/minute")
async def list_history(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=255),
    sort_by: HistorySortBy = Query(default=HistorySortBy.newest),
    date_from: datetime | None = Query(default=None, description="ISO 8601, inclusive"),
    date_to: datetime | None = Query(default=None, description="ISO 8601, inclusive"),
    user: CurrentUser = Depends(get_current_user),
    service: HistoryService = Depends(get_history_service),
) -> PaginatedResponse:
    return await service.list_paginated(
        uuid.UUID(user.id),
        page=page,
        page_size=page_size,
        search=search,
        sort_by=sort_by,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/export")
@limiter.limit("10/minute")
async def export_history(
    request: Request,
    search: str | None = Query(default=None, max_length=255),
    date_from: datetime | None = Query(default=None, description="ISO 8601, inclusive"),
    date_to: datetime | None = Query(default=None, description="ISO 8601, inclusive"),
    user: CurrentUser = Depends(get_current_user),
    service: HistoryService = Depends(get_history_service),
) -> StreamingResponse:
    """Exports the user's calculation history as CSV (SOP §7 "Export
    support"). Declared before `/{calculation_id}` routes in this file's
    ordering isn't actually load-bearing here since no GET /{id} route
    exists, but kept first for readability/consistency with FastAPI's
    path-matching-order convention.
    """
    csv_text = await service.export_csv(
        uuid.UUID(user.id), search=search, date_from=date_from, date_to=date_to
    )
    filename = f"gold-calculator-history-{datetime.utcnow():%Y%m%d-%H%M%S}.csv"
    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("", response_model=CalculationResponse, status_code=201)
@limiter.limit("30/minute")
async def save_history(
    request: Request,
    payload: SaveCalculationRequest,
    user: CurrentUser = Depends(get_current_user),
    service: HistoryService = Depends(get_history_service),
) -> CalculationResponse:
    instance = await service.save(uuid.UUID(user.id), payload)
    return CalculationResponse.model_validate(instance)


@router.put("/{calculation_id}", response_model=CalculationResponse)
@limiter.limit("30/minute")
async def update_history(
    request: Request,
    calculation_id: uuid.UUID,
    payload: UpdateCalculationRequest,
    user: CurrentUser = Depends(get_current_user),
    service: HistoryService = Depends(get_history_service),
) -> CalculationResponse:
    instance = await service.update(uuid.UUID(user.id), calculation_id, payload)
    return CalculationResponse.model_validate(instance)


@router.delete("/{calculation_id}", status_code=204)
@limiter.limit("30/minute")
async def delete_history(
    request: Request,
    calculation_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    service: HistoryService = Depends(get_history_service),
) -> None:
    await service.delete(uuid.UUID(user.id), calculation_id)

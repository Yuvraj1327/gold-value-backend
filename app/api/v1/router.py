from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    auth,
    calculations,
    dashboard,
    gold_rate,
    history,
    loan,
    reports,
    settings,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(gold_rate.router)
api_router.include_router(calculations.router)
api_router.include_router(history.router)
api_router.include_router(settings.router)
api_router.include_router(dashboard.router)
api_router.include_router(loan.router)
api_router.include_router(reports.router)
api_router.include_router(admin.router)

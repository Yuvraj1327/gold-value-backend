"""Dependency-injection wiring: DB session -> repository -> service.

Kept in one place so endpoint modules stay thin and every service always
gets a repository bound to the same request-scoped session.
"""
from __future__ import annotations

import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError
from app.core.security import CurrentUser, get_current_user
from app.database.session import get_db
from app.repositories.calculation_repository import CalculationRepository
from app.repositories.gold_rate_repository import GoldRateRepository
from app.repositories.settings_repository import SettingsRepository
from app.repositories.user_repository import UserRepository
from app.services.admin_service import AdminService
from app.services.auth_service import AuthService
from app.services.calculation_service import CalculationService
from app.services.dashboard_service import DashboardService
from app.services.gold_rate_service import GoldRateService
from app.services.history_service import HistoryService
from app.services.loan_service import LoanService
from app.services.pdf_service import PdfService
from app.services.settings_service import SettingsService


def get_user_repository(session: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(session)


def get_gold_rate_repository(session: AsyncSession = Depends(get_db)) -> GoldRateRepository:
    return GoldRateRepository(session)


def get_calculation_repository(session: AsyncSession = Depends(get_db)) -> CalculationRepository:
    return CalculationRepository(session)


def get_settings_repository(session: AsyncSession = Depends(get_db)) -> SettingsRepository:
    return SettingsRepository(session)


def get_auth_service(user_repo: UserRepository = Depends(get_user_repository)) -> AuthService:
    return AuthService(user_repo)


def get_gold_rate_service(repo: GoldRateRepository = Depends(get_gold_rate_repository)) -> GoldRateService:
    return GoldRateService(repo)


def get_calculation_service() -> CalculationService:
    return CalculationService()


def get_history_service(repo: CalculationRepository = Depends(get_calculation_repository)) -> HistoryService:
    return HistoryService(repo)


def get_settings_service(repo: SettingsRepository = Depends(get_settings_repository)) -> SettingsService:
    return SettingsService(repo)


def get_loan_service(
    calculation_repo: CalculationRepository = Depends(get_calculation_repository),
) -> LoanService:
    return LoanService(calculation_repo)


def get_dashboard_service(
    gold_rate_repo: GoldRateRepository = Depends(get_gold_rate_repository),
    calculation_repo: CalculationRepository = Depends(get_calculation_repository),
) -> DashboardService:
    return DashboardService(gold_rate_repo, calculation_repo)


def get_pdf_service(repo: CalculationRepository = Depends(get_calculation_repository)) -> PdfService:
    return PdfService(repo)


async def get_current_admin(
    user: CurrentUser = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository),
) -> CurrentUser:
    """Role-based authorization gate for admin-only endpoints.

    Looks up the caller's role from our own `users` table (never trusts a
    role claim from the client-supplied JWT, since Supabase tokens don't
    carry app-specific roles) and raises 403 unless it's exactly "admin".
    """
    db_user = await user_repo.get_by_id(uuid.UUID(user.id))
    if db_user is None or db_user.role != "admin":
        raise ForbiddenError("This action requires administrator access.")
    return user


def get_admin_service(
    user_repo: UserRepository = Depends(get_user_repository),
    calculation_repo: CalculationRepository = Depends(get_calculation_repository),
) -> AdminService:
    return AdminService(user_repo, calculation_repo)

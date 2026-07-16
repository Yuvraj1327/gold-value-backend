from __future__ import annotations

import uuid

from app.repositories.calculation_repository import CalculationRepository
from app.repositories.user_repository import UserRepository
from app.schemas.admin import AdminStatsResponse, UserRoleResponse


class AdminService:
    """Backs the admin-only endpoints — every method here is reachable
    only through the `get_current_admin` dependency (role-based
    authorization), never exposed to regular users.
    """

    def __init__(
        self, user_repository: UserRepository, calculation_repository: CalculationRepository
    ) -> None:
        self._user_repository = user_repository
        self._calculation_repository = calculation_repository

    async def get_platform_stats(self) -> AdminStatsResponse:
        total_users = await self._user_repository.count_all()
        total_calculations, total_value = await self._calculation_repository.get_global_stats()
        return AdminStatsResponse(
            total_users=total_users,
            total_calculations=total_calculations,
            total_gold_value_calculated=total_value,
        )

    async def update_user_role(self, target_user_id: uuid.UUID, role: str) -> UserRoleResponse:
        updated = await self._user_repository.update_role(target_user_id, role)
        return UserRoleResponse(id=str(updated.id), email=updated.email, role=updated.role)

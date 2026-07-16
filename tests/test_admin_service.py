from __future__ import annotations

import uuid

import pytest

from app.services.admin_service import AdminService


class _FakeUser:
    def __init__(self, id, email, role):
        self.id = id
        self.email = email
        self.role = role


class _FakeUserRepo:
    def __init__(self, total_users: int, user: _FakeUser | None = None):
        self._total_users = total_users
        self._user = user

    async def count_all(self):
        return self._total_users

    async def update_role(self, user_id, role):
        self._user.role = role
        return self._user


class _FakeCalculationRepo:
    def __init__(self, count: int, total_value: float):
        self._count = count
        self._total_value = total_value

    async def get_global_stats(self):
        return self._count, self._total_value


@pytest.mark.asyncio
async def test_get_platform_stats_aggregates_across_all_users():
    user_repo = _FakeUserRepo(total_users=42)
    calc_repo = _FakeCalculationRepo(count=150, total_value=5_000_000.0)
    service = AdminService(user_repo, calc_repo)

    stats = await service.get_platform_stats()

    assert stats.total_users == 42
    assert stats.total_calculations == 150
    assert stats.total_gold_value_calculated == 5_000_000.0


@pytest.mark.asyncio
async def test_update_user_role_promotes_to_admin():
    target = _FakeUser(id=uuid.uuid4(), email="promote-me@example.com", role="user")
    user_repo = _FakeUserRepo(total_users=1, user=target)
    calc_repo = _FakeCalculationRepo(count=0, total_value=0.0)
    service = AdminService(user_repo, calc_repo)

    result = await service.update_user_role(target.id, "admin")

    assert result.role == "admin"
    assert result.email == "promote-me@example.com"

from __future__ import annotations

import uuid

import pytest

from app.api.deps import get_current_admin
from app.core.exceptions import ForbiddenError
from app.core.security import CurrentUser


class _FakeUser:
    def __init__(self, role: str):
        self.role = role


class _FakeUserRepository:
    def __init__(self, role: str | None):
        self._role = role

    async def get_by_id(self, user_id):
        if self._role is None:
            return None
        return _FakeUser(role=self._role)


@pytest.mark.asyncio
async def test_admin_user_passes_the_gate():
    current_user = CurrentUser(id=str(uuid.uuid4()), email="admin@example.com", is_anonymous=False)
    repo = _FakeUserRepository(role="admin")

    result = await get_current_admin(user=current_user, user_repo=repo)

    assert result is current_user


@pytest.mark.asyncio
async def test_regular_user_is_forbidden():
    current_user = CurrentUser(id=str(uuid.uuid4()), email="user@example.com", is_anonymous=False)
    repo = _FakeUserRepository(role="user")

    with pytest.raises(ForbiddenError):
        await get_current_admin(user=current_user, user_repo=repo)


@pytest.mark.asyncio
async def test_missing_profile_row_is_forbidden():
    """Defensive default: if the users table row somehow doesn't exist yet
    (e.g. the Supabase trigger hasn't fired), treat as non-admin rather
    than erroring or, worse, granting access."""
    current_user = CurrentUser(id=str(uuid.uuid4()), email="ghost@example.com", is_anonymous=False)
    repo = _FakeUserRepository(role=None)

    with pytest.raises(ForbiddenError):
        await get_current_admin(user=current_user, user_repo=repo)


@pytest.mark.asyncio
async def test_guest_anonymous_user_can_still_be_checked():
    """Anonymous/guest sessions go through the exact same role check —
    they'll always be "user" role (never admin) unless explicitly
    promoted, which requires a real account anyway."""
    current_user = CurrentUser(id=str(uuid.uuid4()), email=None, is_anonymous=True)
    repo = _FakeUserRepository(role="user")

    with pytest.raises(ForbiddenError):
        await get_current_admin(user=current_user, user_repo=repo)

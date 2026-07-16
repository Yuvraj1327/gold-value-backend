from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.settings import UserSettings
from app.repositories.base_repository import BaseRepository


class SettingsRepository(BaseRepository[UserSettings]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, UserSettings)

    async def get_by_user_id(self, user_id: uuid.UUID) -> UserSettings | None:
        result = await self.session.execute(select(UserSettings).where(UserSettings.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_or_create_default(self, user_id: uuid.UUID) -> UserSettings:
        existing = await self.get_by_user_id(user_id)
        if existing:
            return existing
        instance = UserSettings(user_id=user_id)
        self.session.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

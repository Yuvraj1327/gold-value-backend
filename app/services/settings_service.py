from __future__ import annotations

import uuid

from app.models.settings import UserSettings
from app.repositories.settings_repository import SettingsRepository
from app.schemas.settings import UpdateSettingsRequest


class SettingsService:
    def __init__(self, repository: SettingsRepository) -> None:
        self._repository = repository

    async def get(self, user_id: uuid.UUID) -> UserSettings:
        return await self._repository.get_or_create_default(user_id)

    async def update(self, user_id: uuid.UUID, payload: UpdateSettingsRequest) -> UserSettings:
        instance = await self._repository.get_or_create_default(user_id)
        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(instance, field, value)
        self._repository.session.add(instance)
        await self._repository.session.commit()
        await self._repository.session.refresh(instance)
        return instance

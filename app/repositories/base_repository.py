"""Generic repository base class.

Concrete repositories inherit this for the common CRUD plumbing and add
their own domain-specific queries on top (see calculation_repository.py
for sorting/pagination/search, which don't generalize well).
"""
from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, session: AsyncSession, model: type[ModelType]) -> None:
        self.session = session
        self.model = model

    async def get_by_id(self, id_value) -> ModelType | None:
        result = await self.session.execute(select(self.model).where(self.model.id == id_value))
        return result.scalar_one_or_none()

    async def add(self, instance: ModelType) -> ModelType:
        self.session.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    async def delete(self, instance: ModelType) -> None:
        await self.session.delete(instance)
        await self.session.commit()

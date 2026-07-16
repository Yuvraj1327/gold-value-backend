from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gold_rate import GoldRate
from app.repositories.base_repository import BaseRepository


class GoldRateRepository(BaseRepository[GoldRate]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, GoldRate)

    async def get_latest(self) -> GoldRate | None:
        result = await self.session.execute(
            select(GoldRate).order_by(GoldRate.updated_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def insert_snapshot(self, rate: GoldRate) -> GoldRate:
        self.session.add(rate)
        await self.session.commit()
        await self.session.refresh(rate)
        return rate

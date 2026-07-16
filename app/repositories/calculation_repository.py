from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calculation import Calculation
from app.repositories.base_repository import BaseRepository
from app.schemas.calculation import HistorySortBy
from app.utils.pagination import PageRequest

_EXPORT_ROW_LIMIT = 5000


class CalculationRepository(BaseRepository[Calculation]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Calculation)

    async def get_by_id_for_user(self, id_value: uuid.UUID, user_id: uuid.UUID) -> Calculation | None:
        result = await self.session.execute(
            select(Calculation).where(Calculation.id == id_value, Calculation.user_id == user_id)
        )
        return result.scalar_one_or_none()

    def _filtered_query(
        self,
        query,
        *,
        user_id: uuid.UUID,
        search: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ):
        query = query.where(Calculation.user_id == user_id)
        if search:
            query = query.where(Calculation.ornament_name.ilike(f"%{search.strip()}%"))
        if date_from:
            query = query.where(Calculation.created_at >= date_from)
        if date_to:
            query = query.where(Calculation.created_at <= date_to)
        return query

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        page_request: PageRequest,
        search: str | None,
        sort_by: HistorySortBy,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[list[Calculation], int]:
        base_query = self._filtered_query(
            select(Calculation), user_id=user_id, search=search, date_from=date_from, date_to=date_to
        )
        count_query = self._filtered_query(
            select(func.count()).select_from(Calculation),
            user_id=user_id,
            search=search,
            date_from=date_from,
            date_to=date_to,
        )

        order_map = {
            HistorySortBy.newest: Calculation.created_at.desc(),
            HistorySortBy.oldest: Calculation.created_at.asc(),
            HistorySortBy.highest_value: Calculation.gold_value.desc(),
            HistorySortBy.lowest_value: Calculation.gold_value.asc(),
        }
        base_query = base_query.order_by(order_map[sort_by])
        base_query = base_query.offset(page_request.offset).limit(page_request.page_size)

        items_result = await self.session.execute(base_query)
        count_result = await self.session.execute(count_query)

        items = list(items_result.scalars().all())
        total = count_result.scalar_one()
        return items, total

    async def list_for_export(
        self,
        user_id: uuid.UUID,
        *,
        search: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[Calculation]:
        """Returns every matching row (newest first), capped at
        `_EXPORT_ROW_LIMIT` as a sane safety bound for a single CSV export
        — well beyond what any real user's history would realistically hit,
        while still protecting the API from an unbounded query."""
        query = self._filtered_query(
            select(Calculation), user_id=user_id, search=search, date_from=date_from, date_to=date_to
        )
        query = query.order_by(Calculation.created_at.desc()).limit(_EXPORT_ROW_LIMIT)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_user_stats(self, user_id: uuid.UUID) -> tuple[int, float]:
        """Returns (total_calculations, total_gold_value_calculated) for
        the Dashboard's statistics section."""
        result = await self.session.execute(
            select(func.count(), func.coalesce(func.sum(Calculation.gold_value), 0)).where(
                Calculation.user_id == user_id
            )
        )
        count, total_value = result.one()
        return count, float(total_value)

    async def get_global_stats(self) -> tuple[int, float]:
        """Same as `get_user_stats` but across every user — used by the
        admin-only aggregate stats endpoint."""
        result = await self.session.execute(
            select(func.count(), func.coalesce(func.sum(Calculation.gold_value), 0))
        )
        count, total_value = result.one()
        return count, float(total_value)

    async def list_recent_for_user(self, user_id: uuid.UUID, limit: int) -> list[Calculation]:
        result = await self.session.execute(
            select(Calculation)
            .where(Calculation.user_id == user_id)
            .order_by(Calculation.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

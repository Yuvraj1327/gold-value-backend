from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.user import User
from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def upsert_profile(self, *, user_id: uuid.UUID, email: str, name: str | None) -> User:
        """Ensures a public.users profile row exists for a Supabase-authenticated user.

        Called defensively on first authenticated request in case the
        Postgres trigger (see supabase/schema.sql) hasn't fired yet — keeps
        the API resilient without depending solely on DB-side triggers.

        Deliberately never touches `role` here — role changes only ever
        happen via `update_role`, so a returning user's admin status is
        never silently reset by this upsert.
        """
        stmt = (
            insert(User)
            .values(id=user_id, email=email, name=name)
            .on_conflict_do_update(
                index_elements=[User.id],
                set_={"email": email, "name": name} if name else {"email": email},
            )
            .returning(User)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one()

    async def update_role(self, user_id: uuid.UUID, role: str) -> User:
        instance = await self.get_by_id(user_id)
        if instance is None:
            raise NotFoundError("User not found.")
        instance.role = role
        self.session.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    async def count_all(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(User))
        return result.scalar_one()

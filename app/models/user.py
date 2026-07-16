"""User profile table.

Supabase Auth owns the `auth.users` table (email/password hashes, OAuth
identities, anonymous flag, etc.) — we never touch it directly. This model
is the public-schema profile row created for every signed-up user (via a
Postgres trigger, see `supabase/schema.sql`), holding only the fields the
app actually displays.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Role-based authorization: "user" (default, all normal app access) or
    # "admin" (unlocks endpoints like manual gold-rate refresh and the
    # aggregate admin dashboard). Never set from client input — only
    # changed via the admin-only PUT /admin/users/{id}/role endpoint,
    # itself gated to existing admins.
    role: Mapped[str] = mapped_column(String(20), nullable=False, server_default="user")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

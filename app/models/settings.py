"""Per-user settings table (one row per user)."""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class UserSettings(Base):
    __tablename__ = "settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    default_ltv: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=75.0)
    default_purity: Mapped[str] = mapped_column(String(10), nullable=False, default="22K")
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="INR")
    auto_rate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    theme: Mapped[str] = mapped_column(String(10), nullable=False, default="system")

    # Defaults applied to new calculations unless the user overrides them
    # on the Add Ornament form (see CalculateRequest / SaveCalculationRequest).
    default_wastage_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    default_making_charges_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    default_gst_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=3.0)

    notifications_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

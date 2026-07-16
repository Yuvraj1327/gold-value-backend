"""Live gold rate snapshot table.

A new row is inserted every time the scheduled refresh job
(`app/services/gold_rate_scheduler.py`) pulls a fresh price. The API always
serves the most recent row by `updated_at`; older rows form a natural price
history usable later for the "Live Gold Charts" future feature.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database.base import Base


class GoldRate(Base):
    __tablename__ = "gold_rates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rate_24k: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    rate_22k: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    rate_20k: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    rate_18k: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

"""Saved gold-value / gold-loan calculation table (per-user history)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database.base import Base


class Calculation(Base):
    __tablename__ = "calculations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ornament_name: Mapped[str] = mapped_column(String(255), nullable=False)
    gross_weight: Mapped[float] = mapped_column(Numeric(10, 3), nullable=False)
    stone_weight: Mapped[float] = mapped_column(Numeric(10, 3), nullable=False, default=0)
    purity: Mapped[float] = mapped_column(Numeric(5, 3), nullable=False)  # e.g. 0.916 for 22K
    gold_rate: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)  # rate per gram used
    ltv_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=75.0)
    wastage_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    making_charges_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    gst_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    pure_gold_weight: Mapped[float] = mapped_column(Numeric(10, 3), nullable=False)
    gold_value: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    making_charges_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    gst_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    final_value: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    loan_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    # Serialised CertificateFormState (customer info, branch, articles, etc.)
    # stored at save-time so History can fully restore the PDF certificate form.
    # NULL for rows saved before this column was added.
    certificate_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)


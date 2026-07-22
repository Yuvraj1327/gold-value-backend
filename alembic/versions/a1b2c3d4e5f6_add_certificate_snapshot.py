"""add certificate_snapshot to calculations

Revision ID: a1b2c3d4e5f6
Revises: 9f92c655f02f
Create Date: 2026-07-22 09:40:00.000000

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "9f92c655f02f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add nullable JSONB column to store the serialised CertificateFormState
    # (customer info, branch, appraiser, articles) captured at save-time.
    # NULL for rows created before this migration — the Flutter app treats
    # NULL as "no snapshot; show empty certificate form" (existing behaviour).
    op.add_column(
        "calculations",
        sa.Column("certificate_snapshot", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("calculations", "certificate_snapshot")

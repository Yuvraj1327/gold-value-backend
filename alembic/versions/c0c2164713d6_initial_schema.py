"""initial schema: users, gold_rates, calculations, settings

Revision ID: c0c2164713d6
Revises:
Create Date: 2026-07-11 00:00:00.000000

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c0c2164713d6"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # users — public profile row, 1:1 with Supabase auth.users
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["id"], ["auth.users.id"], ondelete="CASCADE", name="fk_users_auth_users"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ------------------------------------------------------------------
    # gold_rates
    # ------------------------------------------------------------------
    op.create_table(
        "gold_rates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("rate_24k", sa.Numeric(12, 2), nullable=False),
        sa.Column("rate_22k", sa.Numeric(12, 2), nullable=False),
        sa.Column("rate_20k", sa.Numeric(12, 2), nullable=False),
        sa.Column("rate_18k", sa.Numeric(12, 2), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_gold_rates_updated_at", "gold_rates", ["updated_at"])

    # ------------------------------------------------------------------
    # calculations
    # ------------------------------------------------------------------
    op.create_table(
        "calculations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ornament_name", sa.String(length=255), nullable=False),
        sa.Column("gross_weight", sa.Numeric(10, 3), nullable=False),
        sa.Column("stone_weight", sa.Numeric(10, 3), nullable=False, server_default="0"),
        sa.Column("purity", sa.Numeric(5, 3), nullable=False),
        sa.Column("gold_rate", sa.Numeric(12, 2), nullable=False),
        sa.Column("pure_gold_weight", sa.Numeric(10, 3), nullable=False),
        sa.Column("gold_value", sa.Numeric(14, 2), nullable=False),
        sa.Column("loan_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name="fk_calculations_user_id"
        ),
        sa.CheckConstraint("stone_weight <= gross_weight", name="ck_calculations_stone_le_gross"),
        sa.CheckConstraint("gross_weight > 0", name="ck_calculations_gross_positive"),
        sa.CheckConstraint("purity > 0 AND purity <= 1", name="ck_calculations_purity_range"),
    )
    op.create_index("ix_calculations_user_id", "calculations", ["user_id"])
    op.create_index("ix_calculations_created_at", "calculations", ["created_at"])

    # ------------------------------------------------------------------
    # settings
    # ------------------------------------------------------------------
    op.create_table(
        "settings",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("default_ltv", sa.Numeric(5, 2), nullable=False, server_default="75.0"),
        sa.Column("default_purity", sa.String(length=10), nullable=False, server_default="22K"),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="INR"),
        sa.Column("auto_rate", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("theme", sa.String(length=10), nullable=False, server_default="system"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_settings_user_id"),
    )


def downgrade() -> None:
    op.drop_table("settings")
    op.drop_index("ix_calculations_created_at", table_name="calculations")
    op.drop_index("ix_calculations_user_id", table_name="calculations")
    op.drop_table("calculations")
    op.drop_index("ix_gold_rates_updated_at", table_name="gold_rates")
    op.drop_table("gold_rates")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

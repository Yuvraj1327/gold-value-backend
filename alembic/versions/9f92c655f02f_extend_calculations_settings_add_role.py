# """add role, calculation charges (wastage/making/gst/final_value), settings defaults + notifications

# Revision ID: 9f92c655f02f
# Revises: c0c2164713d6
# Create Date: 2026-07-12 00:00:00.000000

# """
# from __future__ import annotations

# from collections.abc import Sequence

# import sqlalchemy as sa

# from alembic import op

# # revision identifiers, used by Alembic.
# revision: str = "9f92c655f02f"
# down_revision: str | None = "c0c2164713d6"
# branch_labels: str | Sequence[str] | None = None
# depends_on: str | Sequence[str] | None = None


# def upgrade() -> None:
#     # ------------------------------------------------------------------
#     # users.role — role-based authorization ("user" default, "admin" for
#     # gated endpoints like manual gold-rate refresh and /admin/stats).
#     # ------------------------------------------------------------------
#     op.add_column(
#         "users",
#         sa.Column("role", sa.String(length=20), nullable=False, server_default="user"),
#     )

#     # ------------------------------------------------------------------
#     # calculations — ltv_percent (was previously computed but never
#     # persisted, which meant editing any other field on a saved
#     # calculation silently reset its loan basis to a hardcoded 75%) plus
#     # wastage / making charges / GST / final_value.
#     # ------------------------------------------------------------------
#     op.add_column(
#         "calculations",
#         sa.Column("ltv_percent", sa.Numeric(5, 2), nullable=False, server_default="75.0"),
#     )
#     op.add_column(
#         "calculations",
#         sa.Column("wastage_percent", sa.Numeric(5, 2), nullable=False, server_default="0"),
#     )
#     op.add_column(
#         "calculations",
#         sa.Column("making_charges_percent", sa.Numeric(5, 2), nullable=False, server_default="0"),
#     )
#     op.add_column(
#         "calculations",
#         sa.Column("gst_percent", sa.Numeric(5, 2), nullable=False, server_default="0"),
#     )
#     op.add_column(
#         "calculations",
#         sa.Column("making_charges_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
#     )
#     op.add_column(
#         "calculations",
#         sa.Column("gst_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
#     )
#     # final_value backfills from the pre-existing gold_value for any rows
#     # created before this migration (equivalent to 0% making charges/GST).
#     op.add_column(
#         "calculations",
#         sa.Column("final_value", sa.Numeric(14, 2), nullable=True),
#     )
#     op.execute("UPDATE calculations SET final_value = gold_value WHERE final_value IS NULL")
#     op.alter_column("calculations", "final_value", nullable=False)

#     # ------------------------------------------------------------------
#     # settings — default charge percentages + notifications
#     # ------------------------------------------------------------------
#     op.add_column(
#         "settings",
#         sa.Column("default_wastage_percent", sa.Numeric(5, 2), nullable=False, server_default="0"),
#     )
#     op.add_column(
#         "settings",
#         sa.Column("default_making_charges_percent", sa.Numeric(5, 2), nullable=False, server_default="0"),
#     )
#     op.add_column(
#         "settings",
#         sa.Column("default_gst_percent", sa.Numeric(5, 2), nullable=False, server_default="3.0"),
#     )
#     op.add_column(
#         "settings",
#         sa.Column("notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
#     )


# def downgrade() -> None:
#     op.drop_column("settings", "notifications_enabled")
#     op.drop_column("settings", "default_gst_percent")
#     op.drop_column("settings", "default_making_charges_percent")
#     op.drop_column("settings", "default_wastage_percent")

#     op.drop_column("calculations", "final_value")
#     op.drop_column("calculations", "gst_amount")
#     op.drop_column("calculations", "making_charges_amount")
#     op.drop_column("calculations", "gst_percent")
#     op.drop_column("calculations", "making_charges_percent")
#     op.drop_column("calculations", "wastage_percent")
#     op.drop_column("calculations", "ltv_percent")

#     op.drop_column("users", "role")









"""add role, calculation charges (wastage/making/gst/final_value), settings defaults + notifications

Revision ID: 9f92c655f02f
Revises: c0c2164713d6
Create Date: 2026-07-12 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9f92c655f02f"
down_revision: str | None = "c0c2164713d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def column_exists(inspector, table: str, column: str) -> bool:
    return column in [c["name"] for c in inspector.get_columns(table)]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    # ------------------------------------------------------------------
    # users.role
    # ------------------------------------------------------------------
    if not column_exists(inspector, "users", "role"):
        op.add_column(
            "users",
            sa.Column(
                "role",
                sa.String(length=20),
                nullable=False,
                server_default="user",
            ),
        )

    # ------------------------------------------------------------------
    # calculations
    # ------------------------------------------------------------------

    if not column_exists(inspector, "calculations", "ltv_percent"):
        op.add_column(
            "calculations",
            sa.Column(
                "ltv_percent",
                sa.Numeric(5, 2),
                nullable=False,
                server_default="75.0",
            ),
        )

    if not column_exists(inspector, "calculations", "wastage_percent"):
        op.add_column(
            "calculations",
            sa.Column(
                "wastage_percent",
                sa.Numeric(5, 2),
                nullable=False,
                server_default="0",
            ),
        )

    if not column_exists(inspector, "calculations", "making_charges_percent"):
        op.add_column(
            "calculations",
            sa.Column(
                "making_charges_percent",
                sa.Numeric(5, 2),
                nullable=False,
                server_default="0",
            ),
        )

    if not column_exists(inspector, "calculations", "gst_percent"):
        op.add_column(
            "calculations",
            sa.Column(
                "gst_percent",
                sa.Numeric(5, 2),
                nullable=False,
                server_default="0",
            ),
        )

    if not column_exists(inspector, "calculations", "making_charges_amount"):
        op.add_column(
            "calculations",
            sa.Column(
                "making_charges_amount",
                sa.Numeric(14, 2),
                nullable=False,
                server_default="0",
            ),
        )

    if not column_exists(inspector, "calculations", "gst_amount"):
        op.add_column(
            "calculations",
            sa.Column(
                "gst_amount",
                sa.Numeric(14, 2),
                nullable=False,
                server_default="0",
            ),
        )

    final_added = False

    if not column_exists(inspector, "calculations", "final_value"):
        final_added = True

        op.add_column(
            "calculations",
            sa.Column(
                "final_value",
                sa.Numeric(14, 2),
                nullable=True,
            ),
        )

    if final_added:
        op.execute(
            """
            UPDATE calculations
            SET final_value = gold_value
            WHERE final_value IS NULL
            """
        )

        op.alter_column(
            "calculations",
            "final_value",
            nullable=False,
        )

    # ------------------------------------------------------------------
    # settings
    # ------------------------------------------------------------------

    if not column_exists(inspector, "settings", "default_wastage_percent"):
        op.add_column(
            "settings",
            sa.Column(
                "default_wastage_percent",
                sa.Numeric(5, 2),
                nullable=False,
                server_default="0",
            ),
        )

    if not column_exists(inspector, "settings", "default_making_charges_percent"):
        op.add_column(
            "settings",
            sa.Column(
                "default_making_charges_percent",
                sa.Numeric(5, 2),
                nullable=False,
                server_default="0",
            ),
        )

    if not column_exists(inspector, "settings", "default_gst_percent"):
        op.add_column(
            "settings",
            sa.Column(
                "default_gst_percent",
                sa.Numeric(5, 2),
                nullable=False,
                server_default="3.0",
            ),
        )

    if not column_exists(inspector, "settings", "notifications_enabled"):
        op.add_column(
            "settings",
            sa.Column(
                "notifications_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if column_exists(inspector, "settings", "notifications_enabled"):
        op.drop_column("settings", "notifications_enabled")

    if column_exists(inspector, "settings", "default_gst_percent"):
        op.drop_column("settings", "default_gst_percent")

    if column_exists(inspector, "settings", "default_making_charges_percent"):
        op.drop_column("settings", "default_making_charges_percent")

    if column_exists(inspector, "settings", "default_wastage_percent"):
        op.drop_column("settings", "default_wastage_percent")

    if column_exists(inspector, "calculations", "final_value"):
        op.drop_column("calculations", "final_value")

    if column_exists(inspector, "calculations", "gst_amount"):
        op.drop_column("calculations", "gst_amount")

    if column_exists(inspector, "calculations", "making_charges_amount"):
        op.drop_column("calculations", "making_charges_amount")

    if column_exists(inspector, "calculations", "gst_percent"):
        op.drop_column("calculations", "gst_percent")

    if column_exists(inspector, "calculations", "making_charges_percent"):
        op.drop_column("calculations", "making_charges_percent")

    if column_exists(inspector, "calculations", "wastage_percent"):
        op.drop_column("calculations", "wastage_percent")

    if column_exists(inspector, "calculations", "ltv_percent"):
        op.drop_column("calculations", "ltv_percent")

    if column_exists(inspector, "users", "role"):
        op.drop_column("users", "role")
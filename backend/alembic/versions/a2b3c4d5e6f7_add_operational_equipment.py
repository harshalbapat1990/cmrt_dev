"""add_operational_equipment

Revision ID: a2b3c4d5e6f7
Revises: 1a2b3c4d5e6f
Create Date: 2026-04-03 00:00:00.000000

Adds the operational_equipment table for storing reference electricity
consumption data for road-related operational equipment (street lighting,
traffic signals, ITS, etc.).

annual_electricity_consumption_mwh is NOT stored — it is a derived field
computed as: power_kw * hours_per_day * days_per_year / 1000.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "1a2b3c4d5e6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "operational_equipment",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "dataset_revision_id",
            UUID(as_uuid=True),
            sa.ForeignKey("dataset_revisions.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("group_name", sa.String(255), nullable=False),
        sa.Column("item", sa.String(500), nullable=False),
        sa.Column("power_kw", sa.Numeric(12, 6), nullable=False),
        sa.Column("hours_per_day", sa.Numeric(8, 4), nullable=False),
        sa.Column("days_per_year", sa.Numeric(8, 4), nullable=False),
        sa.Column("source", sa.Text, nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    # Partial unique index: item must be unique among global (non-revision) active rows
    op.execute(
        "CREATE UNIQUE INDEX uq_op_eq_global_item "
        "ON operational_equipment (item) "
        "WHERE dataset_revision_id IS NULL AND is_active = TRUE"
    )
    # Partial unique index: (dataset_revision_id, item) among active revision rows
    op.execute(
        "CREATE UNIQUE INDEX uq_op_eq_revision_item "
        "ON operational_equipment (dataset_revision_id, item) "
        "WHERE dataset_revision_id IS NOT NULL AND is_active = TRUE"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_op_eq_revision_item")
    op.execute("DROP INDEX IF EXISTS uq_op_eq_global_item")
    op.drop_table("operational_equipment")

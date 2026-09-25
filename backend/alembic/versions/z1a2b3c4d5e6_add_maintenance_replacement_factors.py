"""add_maintenance_replacement_factors

Revision ID: z1a2b3c4d5e6
Revises: y1z2a3b4c5d6
Create Date: 2026-04-15 00:00:00.000000

Adds the maintenance_replacement_factors table for storing road
maintenance and replacement activity emissions intensities and
default replacement frequencies.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "z1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "y1z2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "maintenance_replacement_factors",
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
            nullable=False,
            index=True,
        ),
        sa.Column(
            "jurisdiction_id",
            UUID(as_uuid=True),
            sa.ForeignKey("jurisdictions.id", ondelete="RESTRICT"),
            nullable=True,
            index=True,
        ),
        sa.Column("activity_type", sa.String(100), nullable=False),
        sa.Column("item", sa.String(255), nullable=False),
        sa.Column("unit_code", sa.String(20), nullable=False, server_default="m2"),
        sa.Column("emissions_intensity_tco2e", sa.Numeric(12, 6), nullable=True),
        sa.Column("default_frequency_years", sa.Integer, nullable=True),
        sa.Column("source_note", sa.Text, nullable=True),
        sa.UniqueConstraint(
            "dataset_revision_id",
            "jurisdiction_id",
            "activity_type",
            "item",
            name="uq_maintenance_replacement_factors",
        ),
    )


def downgrade() -> None:
    op.drop_table("maintenance_replacement_factors")

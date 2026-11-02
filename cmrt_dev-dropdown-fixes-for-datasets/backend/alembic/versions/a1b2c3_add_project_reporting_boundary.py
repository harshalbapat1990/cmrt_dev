"""add_project_reporting_boundary

Revision ID: a1b2c3_add_project_reporting_boundary
Revises: fd1e2a3b4c5d
Create Date: 2026-04-15 00:00:00.000000

Adds project_reporting_boundary table to persist the reporting boundary
entries set during project creation. These entries are later used to
pre-populate mandatory (non-deletable) rows in the data entry tables.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "prjboundary01"
down_revision: Union[str, Sequence[str], None] = "fd1e2a3b4c5d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_reporting_boundary",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("project.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stage_or_activity", sa.String(100), nullable=False),
        sa.Column("category", sa.String(500), nullable=False),
        sa.Column("sub_category", sa.String(500), nullable=False),
        sa.Column("source", sa.String(500), nullable=True),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=False),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_project_reporting_boundary_project_id",
        "project_reporting_boundary",
        ["project_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_project_reporting_boundary_project_id",
        table_name="project_reporting_boundary",
    )
    op.drop_table("project_reporting_boundary")

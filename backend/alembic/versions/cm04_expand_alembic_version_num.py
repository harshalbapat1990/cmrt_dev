"""Widen Alembic's revision storage before long revision IDs are stamped.

Revision ID: cm04_expand_alembic_version_num
Revises: cm04_append_bau_scm_view_column

Alembic creates alembic_version.version_num as VARCHAR(32) by default. Some
repository revision IDs exceed that limit, so widen it before those revisions
are applied and stamped. VARCHAR(255) leaves ample room for future IDs.
"""
from alembic import op
import sqlalchemy as sa


revision = "cm04_expand_alembic_version_num"
down_revision = "cm04_append_bau_scm_view_column"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Widening is safe and idempotent for databases where the column was
    # already expanded manually or by a prior deployment.
    op.alter_column(
        "alembic_version",
        "version_num",
        existing_type=sa.String(length=32),
        type_=sa.String(length=255),
        existing_nullable=False,
    )


def downgrade() -> None:
    # Keep the wider column. It is harmless, and shrinking it could make a
    # later Alembic revision impossible to stamp.
    pass

"""add record_key to densities

Revision ID: fix01_add_record_key_to_densities
Revises: dt01_add_rev_id_vehicles
Create Date: 2026-07-20

The migration c3d4e5f6a7b8 that introduced record_key was on a dead branch
and was never merged into the main chain.  This migration adds the missing
column and its supporting unique indexes to the live database.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "fix01_densities_rec_key"
down_revision: Union[str, Sequence[str], None] = "dt01_add_rev_id_vehicles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the column with a default so existing rows are valid (NOT NULL).
    op.add_column(
        "densities",
        sa.Column("record_key", sa.Text(), nullable=False, server_default=""),
    )
    # Remove the server default now that existing rows have been back-filled.
    op.alter_column("densities", "record_key", server_default=None)

    # Drop stale indexes left by a partially-applied dead-branch migration.
    op.execute("DROP INDEX IF EXISTS uq_densities_global_key")
    op.execute("DROP INDEX IF EXISTS uq_densities_revision_key")

    # Global (revision-less) unique index — safe to create immediately
    # because there are no revision-null rows to conflict.
    op.create_index(
        "uq_densities_global_key",
        "densities",
        ["jurisdiction_id", "dataset", "record_key", "unit_id"],
        unique=True,
        postgresql_where=sa.text("dataset_revision_id IS NULL"),
    )

    # NOTE: uq_densities_revision_key is intentionally omitted here.
    # Existing revision rows all have record_key='' which causes duplicates.
    # The seed_densities script will populate correct record_key values;
    # the index should be added once that has run.


def downgrade() -> None:
    op.drop_index("uq_densities_global_key", table_name="densities")
    op.drop_column("densities", "record_key")


def downgrade() -> None:
    op.drop_index("uq_densities_revision_key", table_name="densities")
    op.drop_index("uq_densities_global_key", table_name="densities")
    op.drop_column("densities", "record_key")

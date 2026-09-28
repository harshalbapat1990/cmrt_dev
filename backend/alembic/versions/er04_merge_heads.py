"""Merge emissions-results and dataset-revision migration branches.

Revision ID: er04_merge_heads
Revises: er03_annual_road_user_results, ds04_unit_conversion_revision
"""

from alembic import op


revision = "er04_merge_heads"
down_revision = ("er03_annual_road_user_results", "ds04_unit_conversion_revision")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

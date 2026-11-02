"""Add dataset_revision_id to recycled_content_factors

Revision ID: rcf01_add_dataset_revision_id
Revises: 0978f35edd0f
Create Date: 2026-05-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'rcf01_add_dataset_revision_id'
down_revision: Union[str, Sequence[str], None] = '0978f35edd0f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add dataset_revision_id FK column to recycled_content_factors."""
    op.add_column(
        "recycled_content_factors",
        sa.Column(
            "dataset_revision_id",
            sa.UUID(),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_rcf_dataset_revision_id",
        "recycled_content_factors",
        "dataset_revisions",
        ["dataset_revision_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_rcf_dataset_revision_id",
        "recycled_content_factors",
        ["dataset_revision_id"],
    )


def downgrade() -> None:
    """Remove dataset_revision_id column from recycled_content_factors."""
    op.drop_index("ix_rcf_dataset_revision_id", table_name="recycled_content_factors")
    op.drop_constraint(
        "fk_rcf_dataset_revision_id",
        "recycled_content_factors",
        type_="foreignkey",
    )
    op.drop_column("recycled_content_factors", "dataset_revision_id")

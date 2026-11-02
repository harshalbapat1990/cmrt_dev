"""make_dataset_revision_id_nullable

Revision ID: 8c9d0e1f2g3h
Revises: 8b9c0d1e2f3g
Create Date: 2026-04-06 12:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '8c9d0e1f2g3h'
down_revision: Union[str, Sequence[str], None] = '8b9c0d1e2f3g'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make dataset_revision_id nullable to allow global carbon values."""
    op.alter_column('carbon_values', 'dataset_revision_id', existing_type=sa.UUID(), nullable=True)


def downgrade() -> None:
    """Restore dataset_revision_id to NOT NULL."""
    op.alter_column('carbon_values', 'dataset_revision_id', existing_type=sa.UUID(), nullable=False)

"""rename_source_comments_to_source

Revision ID: 8b9c0d1e2f3g
Revises: 8a9b0c1d2e3f
Create Date: 2026-04-06 12:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '8b9c0d1e2f3g'
down_revision: Union[str, Sequence[str], None] = '8a9b0c1d2e3f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename source_comments column to source."""
    op.alter_column('carbon_values', 'source_comments', new_column_name='source')


def downgrade() -> None:
    """Rename source back to source_comments."""
    op.alter_column('carbon_values', 'source', new_column_name='source_comments')

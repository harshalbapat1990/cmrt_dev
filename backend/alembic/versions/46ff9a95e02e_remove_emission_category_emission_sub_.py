"""remove_emission_category_emission_sub_category_tables

Revision ID: 46ff9a95e02e
Revises: 8c9d0e1f2g3h
Create Date: 2026-04-07 11:43:34.751691

NOTE: This migration is an intentional no-op placeholder that anchors the
revision chain.  The actual DROP TABLE statements are performed by the
immediately following migration f711b8265c42, which sets its
down_revision = '46ff9a95e02e'.  Do NOT delete this file — removing it
would break Alembic's revision chain.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '46ff9a95e02e'
down_revision: Union[str, Sequence[str], None] = '8c9d0e1f2g3h'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op — see module docstring."""
    pass


def downgrade() -> None:
    """No-op — see module docstring."""
    pass

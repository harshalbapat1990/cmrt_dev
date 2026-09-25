"""merge_report_number_and_ev_uptake_branches

Revision ID: 313465d958d3
Revises: aa2bb3cc4dd5, bb1cc2dd3ee4
Create Date: 2026-04-01 09:58:07.663129

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '313465d958d3'
down_revision: Union[str, Sequence[str], None] = ('aa2bb3cc4dd5', 'bb1cc2dd3ee4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

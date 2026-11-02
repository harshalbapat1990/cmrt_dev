"""merge_datasets_branch_and_development_head

Revision ID: ac2855f1ccb7
Revises: 80d974febc3a, 313465d958d3
Create Date: 2026-04-01 10:21:41.999565

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ac2855f1ccb7'
down_revision: Union[str, Sequence[str], None] = ('80d974febc3a', '313465d958d3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

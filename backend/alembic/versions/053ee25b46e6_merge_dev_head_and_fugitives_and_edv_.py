"""merge dev head and fugitives and EDV migration

Revision ID: 053ee25b46e6
Revises: a2b3c4d5e6f7, z2a3b4c5d6e7
Create Date: 2026-04-05 18:40:54.039189

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '053ee25b46e6'
down_revision: Union[str, Sequence[str], None] = ('a2b3c4d5e6f7', 'z2a3b4c5d6e7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

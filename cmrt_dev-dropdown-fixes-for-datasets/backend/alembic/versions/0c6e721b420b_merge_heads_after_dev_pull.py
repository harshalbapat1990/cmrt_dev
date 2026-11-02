"""merge heads after dev pull

Revision ID: 0c6e721b420b
Revises: b1c2d3e4f5a6, 614d4682d006
Create Date: 2026-04-11 15:39:23.320659

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0c6e721b420b'
down_revision: Union[str, Sequence[str], None] = ('b1c2d3e4f5a6', '614d4682d006')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

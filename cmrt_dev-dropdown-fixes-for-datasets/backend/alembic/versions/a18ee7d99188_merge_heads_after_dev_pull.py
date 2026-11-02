"""merge heads after dev pull

Revision ID: a18ee7d99188
Revises: cp02_fix_period_unique, f711b8265c42
Create Date: 2026-04-10 19:08:49.039000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a18ee7d99188'
down_revision: Union[str, Sequence[str], None] = ('cp02_fix_period_unique', 'f711b8265c42')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

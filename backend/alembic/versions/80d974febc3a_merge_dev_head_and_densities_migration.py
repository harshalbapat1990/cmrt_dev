"""merge dev head and densities migration

Revision ID: 80d974febc3a
Revises: a188fa970589, z1a2b3c4d5e6
Create Date: 2026-03-31 13:59:48.194619

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '80d974febc3a'
down_revision: Union[str, Sequence[str], None] = ('a188fa970589', 'z1a2b3c4d5e6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

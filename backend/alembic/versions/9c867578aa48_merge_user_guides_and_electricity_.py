from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '9c867578aa48'
down_revision: Union[str, Sequence[str], None] = ('era01_electricity_recycling', 'd4e5f6a7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

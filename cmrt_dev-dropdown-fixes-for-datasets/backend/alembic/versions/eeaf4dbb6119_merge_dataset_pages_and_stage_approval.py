"""merge_dataset_pages_and_stage_approval

Revision ID: eeaf4dbb6119
Revises: a7b8c9d0e1f2, n1o2p3q4r5s6
Create Date: 2026-03-18 09:54:35.925572

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eeaf4dbb6119'
down_revision: Union[str, Sequence[str], None] = ('a7b8c9d0e1f2', 'n1o2p3q4r5s6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

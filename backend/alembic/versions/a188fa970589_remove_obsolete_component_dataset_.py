"""Remove obsolete component dataset columns from densities

Revision ID: a188fa970589
Revises: bb1cc2dd3ee4
Create Date: 2026-03-30 14:34:23.466180

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a188fa970589'
down_revision: Union[str, Sequence[str], None] = 'bb1cc2dd3ee4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("densities", "group")
    op.drop_column("densities", "sub_group")
    op.drop_column("densities", "item")
    op.drop_column("densities", "item_description")



def downgrade() -> None:
    op.add_column("densities", sa.Column("group", sa.String(), nullable=True))
    op.add_column("densities", sa.Column("sub_group", sa.String(), nullable=True))
    op.add_column("densities", sa.Column("item", sa.String(), nullable=True))
    op.add_column("densities", sa.Column("item_description", sa.Text(), nullable=True))

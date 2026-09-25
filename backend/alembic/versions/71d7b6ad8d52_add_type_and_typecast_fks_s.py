"""add type and typecast fks's

Revision ID: 71d7b6ad8d52
Revises: cddb18164e47
Create Date: 2026-04-17 18:26:27.774149

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '71d7b6ad8d52'
down_revision: Union[str, Sequence[str], None] = 'cddb18164e47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_foreign_key(
        'fk_project_project_type_id',
        'project',
        'benchmark_mastertypes',
        ['project_type_id'],
        ['id']
    )
    op.create_foreign_key(
        'fk_project_project_typecast_id',
        'project',
        'benchmark_typecasts',
        ['project_typecast_id'],
        ['id']
    )



def downgrade() -> None:
    """Downgrade schema."""
    pass

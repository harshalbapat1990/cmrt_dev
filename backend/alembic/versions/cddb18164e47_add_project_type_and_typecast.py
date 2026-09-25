"""add project type and typecast

Revision ID: cddb18164e47
Revises: z4c5d6e7f8a9
Create Date: 2026-04-17 18:20:08.222747

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'cddb18164e47'
down_revision: Union[str, Sequence[str], None] = 'z4c5d6e7f8a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    # Add new nullable UUID columns
    op.add_column(
        'project',
        sa.Column('project_type_id', UUID(as_uuid=True), nullable=True)
    )

    op.add_column(
        'project',
        sa.Column('project_typecast_id', UUID(as_uuid=True), nullable=True)
    )

    # Drop obsolete legacy column
    op.drop_column('project', 'project_type')


def downgrade() -> None:
    # Restore legacy column
    op.add_column(
        'project',
        sa.Column('project_type', sa.String(200), nullable=True)
    )

    # Drop new UUID columns
    op.drop_column('project', 'project_typecast_id')
    op.drop_column('project', 'project_type_id')

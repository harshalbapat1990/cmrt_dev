"""Add region_id to organization

Revision ID: fd1e2a3b4c5d
Revises: ec2a06c7597e
Create Date: 2026-04-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'fd1e2a3b4c5d'
down_revision: Union[str, Sequence[str], None] = 'ec2a06c7597e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('organization', sa.Column('region_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        op.f('fk__organization__region_id__jurisdictions'),
        'organization', 'jurisdictions',
        ['region_id'], ['id']
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(op.f('fk__organization__region_id__jurisdictions'), 'organization', type_='foreignkey')
    op.drop_column('organization', 'region_id')

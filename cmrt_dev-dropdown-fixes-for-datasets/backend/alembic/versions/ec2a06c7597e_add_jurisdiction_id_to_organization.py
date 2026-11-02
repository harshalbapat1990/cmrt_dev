"""Add jurisdiction_id to organization

Revision ID: ec2a06c7597e
Revises: 88aec3741569
Create Date: 2026-04-14 12:05:57.496555

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ec2a06c7597e'
down_revision: Union[str, Sequence[str], None] = '88aec3741569'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('organization', sa.Column('jurisdiction_id', sa.UUID(), nullable=True))
    op.alter_column('organization', 'id',
               existing_type=sa.UUID(),
               server_default=sa.text('gen_random_uuid()'),
               existing_nullable=False)
    op.drop_constraint(op.f('uq__organization__name'), 'organization', type_='unique')
    op.create_foreign_key(op.f('fk__organization__jurisdiction_id__jurisdictions'), 'organization', 'jurisdictions', ['jurisdiction_id'], ['id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(op.f('fk__organization__jurisdiction_id__jurisdictions'), 'organization', type_='foreignkey')
    op.create_unique_constraint(op.f('uq__organization__name'), 'organization', ['name'])
    op.alter_column('organization', 'id',
               existing_type=sa.UUID(),
               server_default=None,
               existing_nullable=False)
    op.drop_column('organization', 'jurisdiction_id')
    sa.ForeignKeyConstraint(['organisation_id'], ['organization.id'], name=op.f('fk__access_requests__organisation_id__organization'))

    # ### end Alembic commands ###

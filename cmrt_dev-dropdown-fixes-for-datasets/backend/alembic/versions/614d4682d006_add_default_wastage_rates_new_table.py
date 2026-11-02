"""Add default_wastage_rates_new table

Revision ID: 614d4682d006
Revises: a18ee7d99188
Create Date: 2026-04-11 14:01:33.980792

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '614d4682d006'
down_revision: Union[str, Sequence[str], None] = 'a18ee7d99188'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Create default_wastage_rates table."""
    # Create the default_wastage_rates table
    op.create_table(
        'default_wastage_rates',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('dataset_revision_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('jurisdiction_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('material_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('construction_wastage_rate', sa.Numeric(), nullable=False),
        sa.Column('recycling_rate', sa.Numeric(), nullable=False),
        sa.Column('landfill_rate', sa.Numeric(), nullable=False),
        sa.Column('source', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=False), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=False), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['dataset_revision_id'], ['dataset_revisions.id'], name=op.f('fk__default_wastage_rates__dataset_revision_id'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['jurisdiction_id'], ['jurisdictions.id'], name=op.f('fk__default_wastage_rates__jurisdiction_id')),
        sa.ForeignKeyConstraint(['material_id'], ['materials.id'], name=op.f('fk__default_wastage_rates__material_id')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk__default_wastage_rates')),
    )

    # Create indexes
    op.create_index(
        'ix__default_wastage_rates__dataset_revision_id',
        'default_wastage_rates',
        ['dataset_revision_id'],
        unique=False,
    )
    op.create_index(
        'ix__default_wastage_rates__jurisdiction_id',
        'default_wastage_rates',
        ['jurisdiction_id'],
        unique=False,
    )
    op.create_index(
        'ix__default_wastage_rates__material_id',
        'default_wastage_rates',
        ['material_id'],
        unique=False,
    )

    # Create unique constraints for global and revision-specific data
    op.create_index(
        'uq_wastage_rates_global_key',
        'default_wastage_rates',
        ['jurisdiction_id', 'material_id'],
        unique=True,
        postgresql_where=sa.text('dataset_revision_id IS NULL'),
    )
    op.create_index(
        'uq_wastage_rates_revision_key',
        'default_wastage_rates',
        ['jurisdiction_id', 'material_id', 'dataset_revision_id'],
        unique=True,
        postgresql_where=sa.text('dataset_revision_id IS NOT NULL'),
    )


def downgrade() -> None:
    """Downgrade schema - Drop default_wastage_rates table."""
    # Drop indexes
    op.drop_index('uq_wastage_rates_revision_key', table_name='default_wastage_rates')
    op.drop_index('uq_wastage_rates_global_key', table_name='default_wastage_rates')
    op.drop_index('ix__default_wastage_rates__material_id', table_name='default_wastage_rates')
    op.drop_index('ix__default_wastage_rates__jurisdiction_id', table_name='default_wastage_rates')
    op.drop_index('ix__default_wastage_rates__dataset_revision_id', table_name='default_wastage_rates')

    # Drop table
    op.drop_table('default_wastage_rates')

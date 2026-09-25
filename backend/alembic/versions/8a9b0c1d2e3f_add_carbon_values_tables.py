"""add_carbon_values_tables

Revision ID: 8a9b0c1d2e3f
Revises: 053ee25b46e6
Create Date: 2026-04-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8a9b0c1d2e3f'
down_revision: Union[str, Sequence[str], None] = '053ee25b46e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create carbon_value_ranges and carbon_values tables."""
    # Create carbon_value_ranges lookup table
    op.create_table(
        'carbon_value_ranges',
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.PrimaryKeyConstraint('code', name='pk_carbon_value_ranges'),
    )
    op.create_index(
        'ix_carbon_value_ranges_code',
        'carbon_value_ranges',
        ['code'],
        unique=False
    )

    # Create carbon_values table
    op.create_table(
        'carbon_values',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.func.gen_random_uuid(), nullable=False),
        sa.Column('dataset_revision_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('jurisdiction_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('range_code', sa.String(50), nullable=False),
        sa.Column('year', sa.SmallInteger(), nullable=False),
        sa.Column('value', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('currency', sa.String(10), nullable=True),
        sa.Column('source_comments', sa.String(500), nullable=True),
        sa.ForeignKeyConstraint(['dataset_revision_id'], ['dataset_revisions.id'], name='fk_carbon_values_dataset_revision_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['jurisdiction_id'], ['jurisdictions.id'], name='fk_carbon_values_jurisdiction_id'),
        sa.ForeignKeyConstraint(['range_code'], ['carbon_value_ranges.code'], name='fk_carbon_values_range_code'),
        sa.PrimaryKeyConstraint('id', name='pk_carbon_values'),
    )
    
    # Create indexes
    op.create_index(
        'ix_carbon_values_dataset_revision_id',
        'carbon_values',
        ['dataset_revision_id'],
        unique=False
    )
    
    op.create_index(
        'ix_carbon_values_jurisdiction_id',
        'carbon_values',
        ['jurisdiction_id'],
        unique=False
    )
    
    # Create unique constraint
    op.create_index(
        'uq_carbon_value',
        'carbon_values',
        ['dataset_revision_id', 'jurisdiction_id', 'range_code', 'year'],
        unique=True
    )


def downgrade() -> None:
    """Drop carbon_values and carbon_value_ranges tables."""
    op.drop_index('uq_carbon_value', table_name='carbon_values')
    op.drop_index('ix_carbon_values_jurisdiction_id', table_name='carbon_values')
    op.drop_index('ix_carbon_values_dataset_revision_id', table_name='carbon_values')
    op.drop_table('carbon_values')
    op.drop_index('ix_carbon_value_ranges_code', table_name='carbon_value_ranges')
    op.drop_table('carbon_value_ranges')

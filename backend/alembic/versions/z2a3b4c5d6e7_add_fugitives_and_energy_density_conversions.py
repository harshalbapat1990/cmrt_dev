"""add_fugitives_and_energy_density_conversions

Revision ID: z2a3b4c5d6e7
Revises: 1a2b3c4d5e6f
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'z2a3b4c5d6e7'
down_revision = '1a2b3c4d5e6f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create fugitives table
    op.create_table(
        'fugitives',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('dataset_revision_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('jurisdiction_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('equipment_type', sa.String(), nullable=False),
        sa.Column('default_annual_leakage_rate', sa.Numeric(precision=15, scale=6), nullable=True),
        sa.Column('source_comments', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['dataset_revision_id'], ['dataset_revisions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['jurisdiction_id'], ['jurisdictions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create conditional unique indexes for fugitives
    # Index 1: Global records (dataset_revision_id IS NULL)
    op.create_index(
        'uq_fugitives_global',
        'fugitives',
        ['jurisdiction_id', 'equipment_type'],
        unique=True,
        postgresql_where=sa.text('dataset_revision_id IS NULL')
    )
    
    # Index 2: Revision-specific records (dataset_revision_id IS NOT NULL)
    op.create_index(
        'uq_fugitives_revision',
        'fugitives',
        ['jurisdiction_id', 'equipment_type', 'dataset_revision_id'],
        unique=True,
        postgresql_where=sa.text('dataset_revision_id IS NOT NULL')
    )

    # Create energy_density_conversions table
    op.create_table(
        'energy_density_conversions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('dataset_revision_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('unit_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('energy_density', sa.Numeric(precision=15, scale=6), nullable=False),
        sa.Column('source_comments', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['dataset_revision_id'], ['dataset_revisions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['unit_id'], ['units.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create conditional unique indexes for energy_density_conversions
    # Index 1: Global records (dataset_revision_id IS NULL)
    op.create_index(
        'uq_energy_density_conversions_global',
        'energy_density_conversions',
        ['category', 'name', 'unit_id'],
        unique=True,
        postgresql_where=sa.text('dataset_revision_id IS NULL')
    )
    
    # Index 2: Revision-specific records (dataset_revision_id IS NOT NULL)
    op.create_index(
        'uq_energy_density_conversions_revision',
        'energy_density_conversions',
        ['category', 'name', 'unit_id', 'dataset_revision_id'],
        unique=True,
        postgresql_where=sa.text('dataset_revision_id IS NOT NULL')
    )


def downgrade() -> None:
    op.drop_index('uq_energy_density_conversions_revision', table_name='energy_density_conversions')
    op.drop_index('uq_energy_density_conversions_global', table_name='energy_density_conversions')
    op.drop_table('energy_density_conversions')
    op.drop_index('uq_fugitives_revision', table_name='fugitives')
    op.drop_index('uq_fugitives_global', table_name='fugitives')
    op.drop_table('fugitives')

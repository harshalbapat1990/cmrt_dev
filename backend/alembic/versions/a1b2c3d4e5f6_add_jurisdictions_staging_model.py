"""add jurisdictions and staging model package

Revision ID: a1b2c3d4e5f6
Revises: 36cc2dc6aca5
Create Date: 2026-02-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '36cc2dc6aca5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables in the Jurisdictions & Staging Model package."""

    # ------------------------------------------------------------------ #
    # 1. Tables with no foreign-key dependencies first
    # ------------------------------------------------------------------ #

    op.create_table(
        'jurisdictions',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk__jurisdictions')),
        sa.UniqueConstraint('name', name='jurisdictions_name_key'),
    )

    op.create_table(
        'anz_reporting_stages',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk__anz_reporting_stages')),
        sa.UniqueConstraint('name', name='anz_reporting_stages_name_key'),
    )

    op.create_table(
        'ghg_scopes',
        sa.Column('id', sa.SmallInteger(), autoincrement=False, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk__ghg_scopes')),
    )

    op.create_table(
        'units',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('code', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk__units')),
        sa.UniqueConstraint('code', name='units_code_key'),
    )

    # ------------------------------------------------------------------ #
    # 2. Tables that depend on the above
    # ------------------------------------------------------------------ #

    op.create_table(
        'jurisdiction_reporting_stages',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('jurisdiction_id', sa.UUID(), nullable=False),
        sa.Column('anz_reporting_stage_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(
            ['jurisdiction_id'], ['jurisdictions.id'],
            name=op.f('fk__jurisdiction_reporting_stages__jurisdiction_id__jurisdictions'),
        ),
        sa.ForeignKeyConstraint(
            ['anz_reporting_stage_id'], ['anz_reporting_stages.id'],
            name=op.f('fk__jurisdiction_reporting_stages__anz_reporting_stage_id__anz_reporting_stages'),
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk__jurisdiction_reporting_stages')),
        sa.UniqueConstraint(
            'jurisdiction_id', 'name',
            name='jurisdiction_reporting_stages_jurisdiction_id_name_key',
        ),
    )
    op.create_index(
        'jurisdiction_reporting_stages_jurisdiction_id_idx',
        'jurisdiction_reporting_stages', ['jurisdiction_id'], unique=False,
    )
    op.create_index(
        'jurisdiction_reporting_stages_anz_stage_id_idx',
        'jurisdiction_reporting_stages', ['anz_reporting_stage_id'], unique=False,
    )

    op.create_table(
        'unit_conversions',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('from_unit_id', sa.UUID(), nullable=False),
        sa.Column('to_unit_id', sa.UUID(), nullable=False),
        sa.Column('factor', sa.Numeric(), nullable=False),
        sa.ForeignKeyConstraint(
            ['from_unit_id'], ['units.id'],
            name=op.f('fk__unit_conversions__from_unit_id__units'),
        ),
        sa.ForeignKeyConstraint(
            ['to_unit_id'], ['units.id'],
            name=op.f('fk__unit_conversions__to_unit_id__units'),
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk__unit_conversions')),
        sa.UniqueConstraint('from_unit_id', 'to_unit_id', name='unit_conversions_from_unit_id_to_unit_id_key'),
    )
    op.create_index('unit_conversions_from_unit_idx', 'unit_conversions', ['from_unit_id'], unique=False)
    op.create_index('unit_conversions_to_unit_idx', 'unit_conversions', ['to_unit_id'], unique=False)

    # ------------------------------------------------------------------ #
    # 3. emissions_categories — self-referential FK added post-table
    # ------------------------------------------------------------------ #

    op.create_table(
        'emissions_categories',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('code', sa.String(), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('scope', sa.SmallInteger(), nullable=True),
        sa.Column('parent_category_id', sa.UUID(), nullable=True),  # FK added below
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk__emissions_categories')),
    )
    op.create_index('emissions_categories_parent_category_id_idx', 'emissions_categories', ['parent_category_id'], unique=False)
    op.create_index('emissions_categories_scope_idx', 'emissions_categories', ['scope'], unique=False)

    # Self-referential FK added after table exists (name kept <=63 chars for PostgreSQL)
    op.create_foreign_key(
        'fk__emissions_categories__parent_id',
        'emissions_categories', 'emissions_categories',
        ['parent_category_id'], ['id'],
    )


def downgrade() -> None:
    """Drop all tables in reverse dependency order."""

    # Drop self-referential FK first
    op.drop_constraint(
        'fk__emissions_categories__parent_id',
        'emissions_categories', type_='foreignkey',
    )
    op.drop_index('emissions_categories_scope_idx', table_name='emissions_categories')
    op.drop_index('emissions_categories_parent_category_id_idx', table_name='emissions_categories')
    op.drop_table('emissions_categories')

    op.drop_index('unit_conversions_to_unit_idx', table_name='unit_conversions')
    op.drop_index('unit_conversions_from_unit_idx', table_name='unit_conversions')
    op.drop_table('unit_conversions')

    op.drop_index('jurisdiction_reporting_stages_anz_stage_id_idx', table_name='jurisdiction_reporting_stages')
    op.drop_index('jurisdiction_reporting_stages_jurisdiction_id_idx', table_name='jurisdiction_reporting_stages')
    op.drop_table('jurisdiction_reporting_stages')

    op.drop_table('units')
    op.drop_table('ghg_scopes')
    op.drop_table('anz_reporting_stages')
    op.drop_table('jurisdictions')

"""add defaults and materials package

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables in the Defaults & Materials package."""

    # ------------------------------------------------------------------ #
    # 1. Leaf tables with no intra-package dependencies first
    # ------------------------------------------------------------------ #

    op.create_table(
        'materials',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='materials_name_key'),
    )

    op.create_table(
        'waste_treatments',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='waste_treatments_name_key'),
    )

    # ------------------------------------------------------------------ #
    # 2. Tables that depend on materials and/or jurisdictions
    # ------------------------------------------------------------------ #

    op.create_table(
        'material_recycled_content',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('material_id', sa.UUID(), nullable=True),
        sa.Column('recycled_from_material_id', sa.UUID(), nullable=True),
        sa.Column('percent', sa.Numeric(), nullable=True),
        sa.Column('jurisdiction_id', sa.UUID(), nullable=True),
        sa.Column('effective_from', sa.Date(), nullable=True),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(['jurisdiction_id'], ['jurisdictions.id'], name='material_recycled_content_jurisdiction_id_fkey'),
        sa.ForeignKeyConstraint(['material_id'], ['materials.id'], name='material_recycled_content_material_id_fkey'),
        sa.ForeignKeyConstraint(['recycled_from_material_id'], ['materials.id'], name='material_recycled_content_recycled_from_material_id_fkey'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'densities',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('material', sa.String(), nullable=False),
        sa.Column('density', sa.Numeric(), nullable=False),
        sa.Column('unit_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['unit_id'], ['units.id'], name='densities_unit_id_fkey'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('material', 'unit_id', name='densities_material_unit_id_key'),
    )

    op.create_table(
        'default_transport_distances',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('material_or_category', sa.String(), nullable=False),
        sa.Column('jurisdiction_id', sa.UUID(), nullable=False),
        sa.Column('distance_km', sa.Numeric(), nullable=False),
        sa.Column('grade_applicability', sa.String(), nullable=True),
        sa.Column('effective_from', sa.Date(), nullable=True),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(['jurisdiction_id'], ['jurisdictions.id'], name='default_transport_distances_jurisdiction_id_fkey'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('jurisdiction_id', 'material_or_category', name='default_transport_distances_jurisdiction_id_material_key'),
    )

    # ------------------------------------------------------------------ #
    # 3. Tables that depend on materials + waste_treatments + jurisdictions
    # ------------------------------------------------------------------ #

    op.create_table(
        'default_waste_rates',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('jurisdiction_id', sa.UUID(), nullable=False),
        sa.Column('material_id', sa.UUID(), nullable=False),
        sa.Column('waste_treatment_id', sa.UUID(), nullable=False),
        sa.Column('applicable_lifecycle_module_code', sa.String(), nullable=True),
        sa.Column('basis', sa.String(), nullable=False),
        sa.Column('rate', sa.Numeric(), nullable=False),
        sa.Column('rate_unit_id', sa.UUID(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('effective_from', sa.Date(), nullable=True),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(['jurisdiction_id'], ['jurisdictions.id'], name='default_waste_rates_jurisdiction_id_fkey'),
        sa.ForeignKeyConstraint(['material_id'], ['materials.id'], name='default_waste_rates_material_id_fkey'),
        sa.ForeignKeyConstraint(['rate_unit_id'], ['units.id'], name='default_waste_rates_rate_unit_id_fkey'),
        sa.ForeignKeyConstraint(['waste_treatment_id'], ['waste_treatments.id'], name='default_waste_rates_waste_treatment_id_fkey'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'jurisdiction_id', 'material_id', 'waste_treatment_id',
            'applicable_lifecycle_module_code', 'basis',
            name='default_waste_rates_composite_key',
        ),
    )

    # ------------------------------------------------------------------ #
    # 4. base_case_assumptions (depends on optional units)
    # ------------------------------------------------------------------ #

    op.create_table(
        'base_case_assumptions',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('default_value', sa.Numeric(), nullable=True),
        sa.Column('unit_id', sa.UUID(), nullable=True),
        sa.Column('is_anz_default', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['unit_id'], ['units.id'], name='base_case_assumptions_unit_id_fkey'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('category', 'name', name='base_case_assumptions_category_name_key'),
    )

    # ------------------------------------------------------------------ #
    # 5. proponent_assumption_overrides (depends on organization, base_case_assumptions)
    # ------------------------------------------------------------------ #

    op.create_table(
        'proponent_assumption_overrides',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('proponent_org_id', sa.UUID(), nullable=False),
        sa.Column('assumption_id', sa.UUID(), nullable=False),
        sa.Column('value', sa.Numeric(), nullable=True),
        sa.Column('unit_id', sa.UUID(), nullable=True),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(['assumption_id'], ['base_case_assumptions.id'], name='proponent_assumption_overrides_assumption_id_fkey'),
        sa.ForeignKeyConstraint(['proponent_org_id'], ['organization.id'], name='proponent_assumption_overrides_proponent_org_id_fkey'),
        sa.ForeignKeyConstraint(['unit_id'], ['units.id'], name='proponent_assumption_overrides_unit_id_fkey'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'proponent_org_id', 'assumption_id', 'effective_from',
            name='proponent_assumption_overrides_composite_key',
        ),
    )


def downgrade() -> None:
    """Drop all tables in the Defaults & Materials package (reverse dependency order)."""
    op.drop_table('proponent_assumption_overrides')
    op.drop_table('base_case_assumptions')
    op.drop_table('default_waste_rates')
    op.drop_table('default_transport_distances')
    op.drop_table('densities')
    op.drop_table('material_recycled_content')
    op.drop_table('waste_treatments')
    op.drop_table('materials')

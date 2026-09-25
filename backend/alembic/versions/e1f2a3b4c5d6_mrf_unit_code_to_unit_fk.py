"""Replace unit_code varchar with unit_id FK in maintenance_replacement_factors

Revision ID: e1f2a3b4c5d6
Revises: d1e2f3a4b5c6
Create Date: 2026-04-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, Sequence[str], None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop dependent view
    op.execute("DROP VIEW IF EXISTS v_maintenance_replacement_component_level")

    # 2. Add nullable unit_id FK column
    op.add_column(
        'maintenance_replacement_factors',
        sa.Column('unit_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_mrf_unit_id',
        'maintenance_replacement_factors', 'units',
        ['unit_id'], ['id'],
        ondelete='RESTRICT',
    )
    op.create_index(
        'ix_maintenance_replacement_factors_unit_id',
        'maintenance_replacement_factors',
        ['unit_id'],
    )

    # 3. Populate unit_id from existing unit_code values
    op.execute("""
        UPDATE maintenance_replacement_factors mrf
        SET unit_id = u.id
        FROM units u
        WHERE u.code = mrf.unit_code
    """)

    # 4. Drop the old unit_code column
    op.drop_column('maintenance_replacement_factors', 'unit_code')

    # 5. Recreate view joining units table instead of using unit_code column
    op.execute("""
        CREATE VIEW v_maintenance_replacement_component_level AS
        SELECT DISTINCT ON (j.name, mrf.activity_type, mrf.item)
            j.name AS "Jurisdiction",
            mrf.activity_type AS "Activity Type",
            mrf.item AS "Item",
            u.code AS "Unit",
            mrf.emissions_intensity_tco2e AS "Emissions intensity (tCO2e/UoM)",
            mrf.default_frequency_years AS "Default frequency (years)",
            mrf.source_note AS "Source/Comments"
        FROM maintenance_replacement_factors mrf
        JOIN jurisdictions j ON j.id = mrf.jurisdiction_id
        JOIN dataset_revisions dr ON dr.id = mrf.dataset_revision_id
        LEFT JOIN units u ON u.id = mrf.unit_id
        ORDER BY j.name, mrf.activity_type, mrf.item, dr.created_at DESC
    """)


def downgrade() -> None:
    # 1. Drop the updated view
    op.execute("DROP VIEW IF EXISTS v_maintenance_replacement_component_level")

    # 2. Re-add unit_code column
    op.add_column(
        'maintenance_replacement_factors',
        sa.Column('unit_code', sa.String(20), nullable=True),
    )

    # 3. Repopulate unit_code from unit_id join
    op.execute("""
        UPDATE maintenance_replacement_factors mrf
        SET unit_code = u.code
        FROM units u
        WHERE u.id = mrf.unit_id
    """)

    # 4. Set a default for any nulls and make non-nullable
    op.execute("""
        UPDATE maintenance_replacement_factors
        SET unit_code = 'm2'
        WHERE unit_code IS NULL
    """)
    op.alter_column('maintenance_replacement_factors', 'unit_code', nullable=False)

    # 5. Drop unit_id
    op.drop_index('ix_maintenance_replacement_factors_unit_id', table_name='maintenance_replacement_factors')
    op.drop_constraint('fk_mrf_unit_id', 'maintenance_replacement_factors', type_='foreignkey')
    op.drop_column('maintenance_replacement_factors', 'unit_id')

    # 6. Recreate original view using unit_code column
    op.execute("""
        CREATE VIEW v_maintenance_replacement_component_level AS
        SELECT DISTINCT ON (j.name, mrf.activity_type, mrf.item)
            j.name AS "Jurisdiction",
            mrf.activity_type AS "Activity Type",
            mrf.item AS "Item",
            mrf.unit_code AS "Unit",
            mrf.emissions_intensity_tco2e AS "Emissions intensity (tCO2e/UoM)",
            mrf.default_frequency_years AS "Default frequency (years)",
            mrf.source_note AS "Source/Comments"
        FROM maintenance_replacement_factors mrf
        JOIN jurisdictions j ON j.id = mrf.jurisdiction_id
        JOIN dataset_revisions dr ON dr.id = mrf.dataset_revision_id
        ORDER BY j.name, mrf.activity_type, mrf.item, dr.created_at DESC
    """)
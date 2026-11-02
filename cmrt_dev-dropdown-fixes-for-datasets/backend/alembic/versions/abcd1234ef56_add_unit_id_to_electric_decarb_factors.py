"""Add unit_id FK to electric_decarb_factors

Revision ID: abcd1234ef56
Revises: e1f2a3b4c5d6
Create Date: 2026-04-13

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'abcd1234ef56'
down_revision = 'e1f2a3b4c5d6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'electric_decarb_factors',
        sa.Column('unit_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        'fk_edf_unit_id',
        'electric_decarb_factors', 'units',
        ['unit_id'], ['id'],
        ondelete='RESTRICT'
    )
    op.create_index('ix_electric_decarb_factors_unit_id', 'electric_decarb_factors', ['unit_id'])

    # Populate unit_id: renewable_pct → '%', all others → 'tCO2e/MWh'
    op.execute(
        "UPDATE electric_decarb_factors edf "
        "SET unit_id = u.id "
        "FROM units u "
        "WHERE u.code = '%' AND edf.factor_type_code = 'renewable_pct'"
    )
    op.execute(
        "UPDATE electric_decarb_factors edf "
        "SET unit_id = u.id "
        "FROM units u "
        "WHERE u.code = 'tCO2e/MWh' AND edf.factor_type_code != 'renewable_pct'"
    )


def downgrade() -> None:
    op.drop_index('ix_electric_decarb_factors_unit_id', table_name='electric_decarb_factors')
    op.drop_constraint('fk_edf_unit_id', 'electric_decarb_factors', type_='foreignkey')
    op.drop_column('electric_decarb_factors', 'unit_id')

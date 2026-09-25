"""add_declared_unit_to_project

Revision ID: a1b2c3d4
Revises: ds01_direct_substitution_facts
Create Date: 2026-05-20 00:00:00.000000

Adds declared_unit_value (numeric) and declared_unit_type (string) columns
to the project table to support the Cost and Schedule declared unit data entry.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4'
down_revision = 'ds01_direct_substitution_facts'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('project', sa.Column('declared_unit_value', sa.Numeric(18, 4), nullable=True))
    op.add_column('project', sa.Column('declared_unit_type', sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column('project', 'declared_unit_type')
    op.drop_column('project', 'declared_unit_value')

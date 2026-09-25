"""remove_emission_category_emission_sub_category_tables

Revision ID: f711b8265c42
Revises: 46ff9a95e02e
Create Date: 2026-04-07 11:43:47.767661

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f711b8265c42'
down_revision: Union[str, Sequence[str], None] = '46ff9a95e02e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


""" def upgrade():
    op.drop_constraint('emission_source_emissions_sub_category_id_fkey',
                       'emission_source', type_='foreignkey')
    op.drop_table('emission_sub_category')
    op.drop_table('emission_category') """

def upgrade():
    op.execute("""
    ALTER TABLE emission_source
    DROP CONSTRAINT IF EXISTS emission_source_emissions_sub_category_id_fkey;
    """)

    op.execute("""
    DROP TABLE IF EXISTS emission_sub_category CASCADE;
    """)

    op.execute("""
    DROP TABLE IF EXISTS emission_category CASCADE;
    """)

def downgrade():
    pass  # one-way migration

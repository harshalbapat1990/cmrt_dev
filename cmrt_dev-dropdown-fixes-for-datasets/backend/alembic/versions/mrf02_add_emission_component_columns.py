"""add product/transport/installation emission columns to maintenance_replacement_factors

Revision ID: mrf02_add_emission_component_columns
Revises: z1a2b3c4d5e6_add_maintenance_replacement_factors
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "mrf02_emit_cols"
down_revision = "b8lc000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "maintenance_replacement_factors",
        sa.Column("product_emissions_tco2e", sa.Numeric(12, 6), nullable=True),
    )
    op.add_column(
        "maintenance_replacement_factors",
        sa.Column("transport_emissions_tco2e", sa.Numeric(12, 6), nullable=True),
    )
    op.add_column(
        "maintenance_replacement_factors",
        sa.Column("installation_emissions_tco2e", sa.Numeric(12, 6), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("maintenance_replacement_factors", "installation_emissions_tco2e")
    op.drop_column("maintenance_replacement_factors", "transport_emissions_tco2e")
    op.drop_column("maintenance_replacement_factors", "product_emissions_tco2e")

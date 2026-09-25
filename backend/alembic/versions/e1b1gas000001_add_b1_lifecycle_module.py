"""Add B1 (Use Stage - In-Use Gases) to lifecycle_modules

Revision ID: e1b1gas000001
Revises: bfb7c960968a
Create Date: 2026-05-28

Adds the B1 lifecycle module code required by the in-use refrigerant gases
(useB1G2) bridge when writing emissions_results rows.
"""

from alembic import op
import sqlalchemy as sa

revision = "e1b1gas000001"
down_revision = "bfb7c960968a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO lifecycle_modules (code, name, description) VALUES
              ('B1', 'Use Stage - In-Use Emissions',
               'Emissions during the use phase of the asset, including refrigerant gas leakage (EN 15978 B1).')
            ON CONFLICT (code) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM lifecycle_modules WHERE code = 'B1'")
    )

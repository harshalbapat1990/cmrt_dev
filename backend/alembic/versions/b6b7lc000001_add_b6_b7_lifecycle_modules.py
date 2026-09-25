"""Add B6 and B7 lifecycle module codes

Revision ID: b6b7lc000001
Revises: e1b1gas000001
Create Date: 2026-06-02

Adds the B6 (Operational Energy Use) and B7 (Operational Water Use) lifecycle
module codes required by the opEnergy and opEnergyDetailed emission calculators
when writing emissions_results rows.
Without these codes, the FK constraint on emissions_results.lifecycle_module_code
causes a session rollback which propagates as a 500 on POST /api/activity-data.
"""

from alembic import op
import sqlalchemy as sa

revision = "b6b7lc000001"
down_revision = "e1b1gas000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO lifecycle_modules (code, name, description) VALUES
              ('B6', 'Operational Energy Use',
               'Energy use during the operational phase of the asset (EN 15978 B6).'),
              ('B7', 'Operational Water Use',
               'Water use during the operational phase of the asset (EN 15978 B7).')
            ON CONFLICT (code) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM lifecycle_modules WHERE code IN ('B6', 'B7')
            """
        )
    )

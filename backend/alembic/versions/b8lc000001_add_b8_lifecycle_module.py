"""add B8 lifecycle module

Revision ID: b8lc000001
Revises: b6b7lc000001
Create Date: 2025-01-01 00:00:00.000000

Adds B8 (Road/Transport User Emissions) to the lifecycle_modules reference table.
Currently B8 values are read from activity_data.extra_fields (TIER 2 approach);
once the calculation services write to emissions_results this entry will be
required for the FK constraint on emissions_results.lifecycle_module_code.
"""

from typing import Union, Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b8lc000001"
down_revision: Union[str, Sequence[str], None] = "b6b7lc000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text("""
            INSERT INTO lifecycle_modules (code, name, description) VALUES
              ('B8', 'Road and Transport User Emissions',
               'Emissions from road and transport users during the use stage of the asset (EN 15978 B8).')
            ON CONFLICT (code) DO NOTHING
        """)
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM lifecycle_modules WHERE code = 'B8'")
    )

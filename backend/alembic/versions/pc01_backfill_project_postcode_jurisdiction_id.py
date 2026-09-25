"""Backfill jurisdiction_id on project_postcode from postcode_reference

Revision ID: pc01_backfill_pc_jur
Revises: pm01_add_pm
Create Date: 2026-05-05 00:00:00.000000

For every project_postcode row that has a NULL jurisdiction_id, copy it from
the matching postcode_reference row (matched on postcode string). This fixes
existing projects that had their postcodes saved before the
`get_project_grid_context` endpoint was updated to check jurisdiction.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "pc01_backfill_pc_jur"
down_revision: Union[str, Sequence[str], None] = "pm01_add_pm"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE project_postcode pp
        SET    jurisdiction_id = pr.jurisdiction_id
        FROM   postcode_reference pr
        WHERE  pr.postcode        = pp.postcode
          AND  pp.jurisdiction_id IS NULL
          AND  pr.jurisdiction_id IS NOT NULL
        """
    )


def downgrade() -> None:
    # Nullify the backfilled values — we can identify them because
    # they were set from postcode_reference, but there's no reliable way
    # to distinguish them from legitimately-set values after the fact.
    # A safe downgrade is a no-op; re-running the previous migration
    # doesn't drop the column.
    pass

"""fix_unit_id_fk

Revision ID: y1z2a3b4c5d6
Revises: x1y2z3a4b5c6
Create Date: 2026-03-28 00:00:00.000000

activity_data.unit_id and emissions_results.unit_id were incorrectly
referencing the 'units' table (a legacy code-only table).  The frontend
drives unit selection from /lookup/measurement-units which reads
measurement_unit.id.  Fix both FK constraints.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "y1z2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "x1y2z3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── activity_data.unit_id ─────────────────────────────────────────────
    # drop old FK to units, add FK to measurement_unit, make nullable
    op.drop_constraint("fk__activity_data__unit_id__units", "activity_data", type_="foreignkey")
    op.alter_column("activity_data", "unit_id", nullable=True)
    op.create_foreign_key(
        "fk__activity_data__unit_id__measurement_unit",
        "activity_data", "measurement_unit",
        ["unit_id"], ["id"],
        ondelete="RESTRICT",
    )

    # ── emissions_results.unit_id ─────────────────────────────────────────
    # drop old FK to units (already nullable, just remove the constraint)
    op.drop_constraint("fk__emissions_results__unit_id__units", "emissions_results", type_="foreignkey")


def downgrade() -> None:
    op.drop_constraint("fk__activity_data__unit_id__measurement_unit", "activity_data", type_="foreignkey")
    op.alter_column("activity_data", "unit_id", nullable=False)
    op.create_foreign_key(
        "fk__activity_data__unit_id__units",
        "activity_data", "units",
        ["unit_id"], ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk__emissions_results__unit_id__units",
        "emissions_results", "units",
        ["unit_id"], ["id"],
        ondelete="RESTRICT",
    )

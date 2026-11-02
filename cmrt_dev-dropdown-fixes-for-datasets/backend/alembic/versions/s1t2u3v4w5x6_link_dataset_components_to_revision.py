"""Link all dataset component tables to dataset_revisions

Revision ID: s1t2u3v4w5x6
Revises: r1s2t3u4v5w6
Create Date: 2026-03-19

Per spec: A dataset revision is a complete, governable package of ALL background
data needed for calculations — not just emission factors. This migration adds a
nullable dataset_revision_id FK to the five supporting tables so every component
can be tied to a specific revision:

  • default_transport_distances
  • default_waste_rates
  • densities
  • material_recycled_content
  • base_case_assumptions

Nullable because:
  • Existing rows are "global/temporal" defaults with no revision context.
    They remain valid and are returned when no revision_id is specified.
  • New rows created inside a particular revision will carry the FK.

Branching will copy revision-scoped rows; global rows are inherited as fallback.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "s1t2u3v4w5x6"
down_revision = "r1s2t3u4v5w6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    fk_col = sa.Column(
        "dataset_revision_id",
        postgresql.UUID(as_uuid=True),
        nullable=True,
    )

    for table in (
        "default_transport_distances",
        "default_waste_rates",
        "densities",
        "material_recycled_content",
        "base_case_assumptions",
    ):
        op.add_column(table, fk_col.copy())
        op.create_foreign_key(
            f"fk_{table}_dataset_revision_id",
            table,
            "dataset_revisions",
            ["dataset_revision_id"],
            ["id"],
            ondelete="CASCADE",
        )
        op.create_index(
            f"ix_{table}_dataset_revision_id",
            table,
            ["dataset_revision_id"],
        )


def downgrade() -> None:
    for table in (
        "default_transport_distances",
        "default_waste_rates",
        "densities",
        "material_recycled_content",
        "base_case_assumptions",
    ):
        op.drop_index(f"ix_{table}_dataset_revision_id", table_name=table)
        op.drop_constraint(f"fk_{table}_dataset_revision_id", table, type_="foreignkey")
        op.drop_column(table, "dataset_revision_id")

"""extend densities and recycled_content for CSV seeding

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-04 00:00:00.000000

Changes:
- Drops `densities` table and recreates with full descriptive schema
  (jurisdiction_id, dataset, record_key, group, sub_group, item,
   item_description, emissions_category, emissions_sub_category,
   emissions_source, density, unit_id, source)
- Adds `notes` column to `material_recycled_content`
- Adds unique constraint (jurisdiction_id, material_id) to
  `material_recycled_content` for idempotent CSV seeding
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1.  Densities — drop old minimal table, recreate with full schema
    # ------------------------------------------------------------------
    op.drop_table("densities")

    op.create_table(
        "densities",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),

        # Scope
        sa.Column("jurisdiction_id", sa.UUID(), nullable=True),
        sa.Column("dataset", sa.String(), nullable=False),      # 'component' | 'detailed'
        sa.Column("record_key", sa.Text(), nullable=False),     # natural key for idempotency

        # Component-level columns (Component-Level Densities CSV)
        sa.Column("group", sa.String(), nullable=True),
        sa.Column("sub_group", sa.String(), nullable=True),
        sa.Column("item", sa.String(), nullable=True),
        sa.Column("item_description", sa.Text(), nullable=True),

        # Detailed-level columns (Detailed-Level Densities CSV)
        sa.Column("emissions_category", sa.String(), nullable=True),
        sa.Column("emissions_sub_category", sa.String(), nullable=True),
        sa.Column("emissions_source", sa.Text(), nullable=True),

        # Measurement
        sa.Column("density", sa.Numeric(), nullable=True),
        sa.Column("unit_id", sa.UUID(), nullable=False),
        sa.Column("source", sa.Text(), nullable=True),

        sa.ForeignKeyConstraint(["jurisdiction_id"], ["jurisdictions.id"],
                                name="densities_jurisdiction_id_fkey"),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"],
                                name="densities_unit_id_fkey"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "jurisdiction_id", "dataset", "record_key", "unit_id",
            name="densities_jurisdiction_dataset_record_key_unit_key",
        ),
    )

    # ------------------------------------------------------------------
    # 2.  material_recycled_content — add notes column + unique constraint
    # ------------------------------------------------------------------
    op.add_column(
        "material_recycled_content",
        sa.Column("notes", sa.Text(), nullable=True),
    )

    op.create_unique_constraint(
        "material_recycled_content_jurisdiction_material_key",
        "material_recycled_content",
        ["jurisdiction_id", "material_id"],
    )


def downgrade() -> None:
    # Reverse: remove constraint + notes from material_recycled_content
    op.drop_constraint(
        "material_recycled_content_jurisdiction_material_key",
        "material_recycled_content",
        type_="unique",
    )
    op.drop_column("material_recycled_content", "notes")

    # Reverse: drop new densities, recreate original minimal table
    op.drop_table("densities")

    op.create_table(
        "densities",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("material", sa.String(), nullable=False),
        sa.Column("density", sa.Numeric(), nullable=False),
        sa.Column("unit_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], name="densities_unit_id_fkey"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("material", "unit_id", name="densities_material_unit_id_key"),
    )

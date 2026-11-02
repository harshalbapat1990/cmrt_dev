"""Extend default_transport_distances: per-mode distances, mode labels, source, distance_unit_id FK.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-03-05

Changes vs previous schema:
- Drop legacy single `distance_km` column (not expressive enough for multi-mode data).
- Drop old 3-column unique constraint (replaced by two partial unique indexes).
- Add per-mode numeric distance columns: truck_distance, rail_distance, sea_distance.
- Add shared distance unit FK: distance_unit_id → units.id.
- Add per-mode label columns: truck_transport_mode, rail_transport_mode, sea_transport_mode.
- Add source text column.
- Add CHECK constraint: exactly one of material_id or emissions_category_id must be set.
- Add partial unique index on (jurisdiction_id, emissions_category_id) where emissions_category_id IS NOT NULL.
- Add partial unique index on (jurisdiction_id, material_id) where material_id IS NOT NULL.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Drop legacy single distance column
    op.drop_column("default_transport_distances", "distance_km")

    # 2. Drop old 3-column unique constraint
    op.drop_constraint(
        "default_transport_distances_jurisdiction_material_category_key",
        "default_transport_distances",
        type_="unique",
    )

    # 3. Add per-mode distance columns (nullable — not all modes used by every row)
    op.add_column("default_transport_distances", sa.Column("truck_distance", sa.Numeric(), nullable=True))
    op.add_column("default_transport_distances", sa.Column("rail_distance", sa.Numeric(), nullable=True))
    op.add_column("default_transport_distances", sa.Column("sea_distance", sa.Numeric(), nullable=True))

    # 4. Add shared distance unit FK
    op.add_column(
        "default_transport_distances",
        sa.Column("distance_unit_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_dtd_distance_unit",
        "default_transport_distances",
        "units",
        ["distance_unit_id"],
        ["id"],
    )

    # 5. Add mode label columns
    op.add_column("default_transport_distances", sa.Column("truck_transport_mode", sa.String(), nullable=True))
    op.add_column("default_transport_distances", sa.Column("rail_transport_mode", sa.String(), nullable=True))
    op.add_column("default_transport_distances", sa.Column("sea_transport_mode", sa.String(), nullable=True))

    # 6. Add source column
    op.add_column("default_transport_distances", sa.Column("source", sa.Text(), nullable=True))

    # 7. Add CHECK: exactly one of material_id / emissions_category_id set
    op.create_check_constraint(
        "chk_dtd_exactly_one_key",
        "default_transport_distances",
        "num_nonnulls(material_id, emissions_category_id) = 1",
    )

    # 8. Partial unique index: one row per (jurisdiction, category)
    op.execute(
        "CREATE UNIQUE INDEX uq_dtd_jurisdiction_category "
        "ON default_transport_distances (jurisdiction_id, emissions_category_id) "
        "WHERE emissions_category_id IS NOT NULL"
    )

    # 9. Partial unique index: one row per (jurisdiction, material)
    op.execute(
        "CREATE UNIQUE INDEX uq_dtd_jurisdiction_material "
        "ON default_transport_distances (jurisdiction_id, material_id) "
        "WHERE material_id IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_dtd_jurisdiction_material")
    op.execute("DROP INDEX IF EXISTS uq_dtd_jurisdiction_category")

    op.drop_constraint("chk_dtd_exactly_one_key", "default_transport_distances", type_="check")
    op.drop_column("default_transport_distances", "source")
    op.drop_column("default_transport_distances", "sea_transport_mode")
    op.drop_column("default_transport_distances", "rail_transport_mode")
    op.drop_column("default_transport_distances", "truck_transport_mode")
    op.drop_constraint("fk_dtd_distance_unit", "default_transport_distances", type_="foreignkey")
    op.drop_column("default_transport_distances", "distance_unit_id")
    op.drop_column("default_transport_distances", "sea_distance")
    op.drop_column("default_transport_distances", "rail_distance")
    op.drop_column("default_transport_distances", "truck_distance")

    op.create_unique_constraint(
        "default_transport_distances_jurisdiction_material_category_key",
        "default_transport_distances",
        ["jurisdiction_id", "material_id", "emissions_category_id"],
    )
    op.add_column("default_transport_distances", sa.Column("distance_km", sa.Numeric(), nullable=False))

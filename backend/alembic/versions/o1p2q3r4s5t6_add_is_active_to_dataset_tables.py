"""add_is_active_to_dataset_tables

Revision ID: o1p2q3r4s5t6
Revises: eeaf4dbb6119
Create Date: 2025-01-01 00:00:00.000000

Adds is_active boolean column to material_recycled_content,
default_transport_distances, and default_waste_rates.
Drops existing unique constraints and replaces them with
partial unique indexes WHERE is_active = TRUE so that
superseded (inactive) rows can coexist without violating uniqueness.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "o1p2q3r4s5t6"
down_revision = "eeaf4dbb6119"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── material_recycled_content ────────────────────────────────────────────
    op.add_column(
        "material_recycled_content",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.drop_constraint(
        "material_recycled_content_jurisdiction_material_key",
        "material_recycled_content",
        type_="unique",
    )
    op.create_index(
        "uq_mrc_active_jurisdiction_material",
        "material_recycled_content",
        ["jurisdiction_id", "material_id"],
        unique=True,
        postgresql_where=sa.text("is_active = TRUE"),
    )

    # ── default_transport_distances ──────────────────────────────────────────
    op.add_column(
        "default_transport_distances",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.drop_index("uq_dtd_jurisdiction_category", table_name="default_transport_distances")
    op.drop_index("uq_dtd_jurisdiction_material", table_name="default_transport_distances")
    op.create_index(
        "uq_dtd_active_jurisdiction_category",
        "default_transport_distances",
        ["jurisdiction_id", "emissions_category_id"],
        unique=True,
        postgresql_where=sa.text("emissions_category_id IS NOT NULL AND is_active = TRUE"),
    )
    op.create_index(
        "uq_dtd_active_jurisdiction_material",
        "default_transport_distances",
        ["jurisdiction_id", "material_id"],
        unique=True,
        postgresql_where=sa.text("material_id IS NOT NULL AND is_active = TRUE"),
    )

    # ── default_waste_rates ──────────────────────────────────────────────────
    op.add_column(
        "default_waste_rates",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.drop_constraint(
        "default_waste_rates_composite_key",
        "default_waste_rates",
        type_="unique",
    )
    op.create_index(
        "uq_dwr_active_composite",
        "default_waste_rates",
        ["jurisdiction_id", "material_id", "waste_treatment_id", "applicable_lifecycle_module_code", "basis"],
        unique=True,
        postgresql_where=sa.text("is_active = TRUE"),
    )


def downgrade() -> None:
    # ── default_waste_rates ──────────────────────────────────────────────────
    op.drop_index("uq_dwr_active_composite", table_name="default_waste_rates")
    op.create_unique_constraint(
        "default_waste_rates_composite_key",
        "default_waste_rates",
        ["jurisdiction_id", "material_id", "waste_treatment_id", "applicable_lifecycle_module_code", "basis"],
    )
    op.drop_column("default_waste_rates", "is_active")

    # ── default_transport_distances ──────────────────────────────────────────
    op.drop_index("uq_dtd_active_jurisdiction_material", table_name="default_transport_distances")
    op.drop_index("uq_dtd_active_jurisdiction_category", table_name="default_transport_distances")
    op.create_index(
        "uq_dtd_jurisdiction_material",
        "default_transport_distances",
        ["jurisdiction_id", "material_id"],
        unique=True,
        postgresql_where=sa.text("material_id IS NOT NULL"),
    )
    op.create_index(
        "uq_dtd_jurisdiction_category",
        "default_transport_distances",
        ["jurisdiction_id", "emissions_category_id"],
        unique=True,
        postgresql_where=sa.text("emissions_category_id IS NOT NULL"),
    )
    op.drop_column("default_transport_distances", "is_active")

    # ── material_recycled_content ────────────────────────────────────────────
    op.drop_index("uq_mrc_active_jurisdiction_material", table_name="material_recycled_content")
    op.create_unique_constraint(
        "material_recycled_content_jurisdiction_material_key",
        "material_recycled_content",
        ["jurisdiction_id", "material_id"],
    )
    op.drop_column("material_recycled_content", "is_active")

"""Update dataset component unique constraints to be revision-aware.

Revision ID: t1u2v3w4x5y6
Revises: s1t2u3v4w5x6
Create Date: 2026-03-19

Problem: the original partial unique indexes on default_transport_distances,
default_waste_rates, material_recycled_content and densities enforce uniqueness
across ALL rows, regardless of their dataset_revision_id.  Once we allow
multiple revisions to each carry their own copy of a row (same jurisdiction +
material but different revision_id), those indexes immediately fire.

Fix: split every affected index into two:
  - "global" variant: applies WHERE dataset_revision_id IS NULL  (legacy rows)
  - "revision" variant: applies WHERE dataset_revision_id IS NOT NULL
    and includes dataset_revision_id in the key columns.
"""

from alembic import op

revision = "t1u2v3w4x5y6"
down_revision = "s1t2u3v4w5x6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── default_transport_distances ─────────────────────────────────────────
    op.drop_index(
        "uq_dtd_active_jurisdiction_category",
        table_name="default_transport_distances",
    )
    op.drop_index(
        "uq_dtd_active_jurisdiction_material",
        table_name="default_transport_distances",
    )

    # global (NULL revision) — keep original semantics
    op.create_index(
        "uq_dtd_global_category",
        "default_transport_distances",
        ["jurisdiction_id", "emissions_category_id"],
        unique=True,
        postgresql_where=(
            "emissions_category_id IS NOT NULL AND is_active = TRUE "
            "AND dataset_revision_id IS NULL"
        ),
    )
    op.create_index(
        "uq_dtd_global_material",
        "default_transport_distances",
        ["jurisdiction_id", "material_id"],
        unique=True,
        postgresql_where=(
            "material_id IS NOT NULL AND is_active = TRUE "
            "AND dataset_revision_id IS NULL"
        ),
    )
    # revision-scoped: unique per (jurisdiction, target, revision)
    op.create_index(
        "uq_dtd_revision_category",
        "default_transport_distances",
        ["jurisdiction_id", "emissions_category_id", "dataset_revision_id"],
        unique=True,
        postgresql_where=(
            "emissions_category_id IS NOT NULL AND is_active = TRUE "
            "AND dataset_revision_id IS NOT NULL"
        ),
    )
    op.create_index(
        "uq_dtd_revision_material",
        "default_transport_distances",
        ["jurisdiction_id", "material_id", "dataset_revision_id"],
        unique=True,
        postgresql_where=(
            "material_id IS NOT NULL AND is_active = TRUE "
            "AND dataset_revision_id IS NOT NULL"
        ),
    )

    # ── default_waste_rates ─────────────────────────────────────────────────
    op.drop_index("uq_dwr_active_composite", table_name="default_waste_rates")
    op.create_index(
        "uq_dwr_global_composite",
        "default_waste_rates",
        [
            "jurisdiction_id", "material_id", "waste_treatment_id",
            "applicable_lifecycle_module_code", "basis",
        ],
        unique=True,
        postgresql_where="is_active = TRUE AND dataset_revision_id IS NULL",
    )
    op.create_index(
        "uq_dwr_revision_composite",
        "default_waste_rates",
        [
            "jurisdiction_id", "material_id", "waste_treatment_id",
            "applicable_lifecycle_module_code", "basis", "dataset_revision_id",
        ],
        unique=True,
        postgresql_where="is_active = TRUE AND dataset_revision_id IS NOT NULL",
    )

    # ── material_recycled_content ────────────────────────────────────────────
    op.drop_index(
        "uq_mrc_active_jurisdiction_material",
        table_name="material_recycled_content",
    )
    op.create_index(
        "uq_mrc_global_jurisdiction_material",
        "material_recycled_content",
        ["jurisdiction_id", "material_id"],
        unique=True,
        postgresql_where="is_active = TRUE AND dataset_revision_id IS NULL",
    )
    op.create_index(
        "uq_mrc_revision_jurisdiction_material",
        "material_recycled_content",
        ["jurisdiction_id", "material_id", "dataset_revision_id"],
        unique=True,
        postgresql_where="is_active = TRUE AND dataset_revision_id IS NOT NULL",
    )

    # ── densities ───────────────────────────────────────────────────────────
    # Original was a full UNIQUE CONSTRAINT (no WHERE clause).
    # Replace with two partial unique indexes.
    op.drop_constraint(
        "densities_jurisdiction_dataset_record_key_unit_key",
        "densities",
        type_="unique",
    )
    op.create_index(
        "uq_densities_global_key",
        "densities",
        ["jurisdiction_id", "dataset", "record_key", "unit_id"],
        unique=True,
        postgresql_where="dataset_revision_id IS NULL",
    )
    op.create_index(
        "uq_densities_revision_key",
        "densities",
        ["jurisdiction_id", "dataset", "record_key", "unit_id", "dataset_revision_id"],
        unique=True,
        postgresql_where="dataset_revision_id IS NOT NULL",
    )


def downgrade() -> None:
    # densities
    op.drop_index("uq_densities_revision_key", table_name="densities")
    op.drop_index("uq_densities_global_key",   table_name="densities")
    op.create_unique_constraint(
        "densities_jurisdiction_dataset_record_key_unit_key",
        "densities",
        ["jurisdiction_id", "dataset", "record_key", "unit_id"],
    )

    # material_recycled_content
    op.drop_index("uq_mrc_revision_jurisdiction_material", table_name="material_recycled_content")
    op.drop_index("uq_mrc_global_jurisdiction_material",   table_name="material_recycled_content")
    op.create_index(
        "uq_mrc_active_jurisdiction_material",
        "material_recycled_content",
        ["jurisdiction_id", "material_id"],
        unique=True,
        postgresql_where="is_active = TRUE",
    )

    # default_waste_rates
    op.drop_index("uq_dwr_revision_composite", table_name="default_waste_rates")
    op.drop_index("uq_dwr_global_composite",   table_name="default_waste_rates")
    op.create_index(
        "uq_dwr_active_composite",
        "default_waste_rates",
        [
            "jurisdiction_id", "material_id", "waste_treatment_id",
            "applicable_lifecycle_module_code", "basis",
        ],
        unique=True,
        postgresql_where="is_active = TRUE",
    )

    # default_transport_distances
    op.drop_index("uq_dtd_revision_material", table_name="default_transport_distances")
    op.drop_index("uq_dtd_revision_category", table_name="default_transport_distances")
    op.drop_index("uq_dtd_global_material",   table_name="default_transport_distances")
    op.drop_index("uq_dtd_global_category",   table_name="default_transport_distances")
    op.create_index(
        "uq_dtd_active_jurisdiction_category",
        "default_transport_distances",
        ["jurisdiction_id", "emissions_category_id"],
        unique=True,
        postgresql_where="emissions_category_id IS NOT NULL AND is_active = TRUE",
    )
    op.create_index(
        "uq_dtd_active_jurisdiction_material",
        "default_transport_distances",
        ["jurisdiction_id", "material_id"],
        unique=True,
        postgresql_where="material_id IS NOT NULL AND is_active = TRUE",
    )

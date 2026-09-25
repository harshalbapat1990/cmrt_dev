"""
BGM full FK normalisation:
  - Create lifecycle_modules table
  - background_grade_metrics: replace string emissions_category/subcategory
    columns with UUID FKs to emissions_categories, and add FK on
    lifecycle_module_code → lifecycle_modules.code
  - default_waste_rates: add FK on applicable_lifecycle_module_code
"""
from alembic import op
import sqlalchemy as sa

revision = "l1m2n3o4p5q6"
down_revision = "k1l2m3n4o5p6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # 1. Create lifecycle_modules lookup table
    # ------------------------------------------------------------------ #
    op.create_table(
        "lifecycle_modules",
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("code"),
    )

    # Seed lifecycle module codes inline so FK constraints added below are valid
    op.execute(
        sa.text(
            """
            INSERT INTO lifecycle_modules (code, name, description) VALUES
              ('A1-A3', 'Product Stage',
               'Raw material extraction, transport and manufacturing (EN 15978 A1-A3).'),
              ('A4',    'Transport to Site',
               'Transport of products to the building site (EN 15978 A4).'),
              ('A5',    'Construction Process',
               'Installation into the building / construction process (EN 15978 A5).'),
              ('A1-A5', 'Full Construction Phase',
               'Combined product, transport and construction phases (EN 15978 A1-A5).'),
              ('B2-5',  'Use Stage',
               'Maintenance, repair, replacement, refurbishment (EN 15978 B2-B5).'),
              ('C2',    'Transport to Waste',
               'Transport to waste processing facility (EN 15978 C2).'),
              ('C3-4',  'Waste Processing and Disposal',
               'Waste processing and disposal (EN 15978 C3-C4).')
            ON CONFLICT (code) DO NOTHING
            """
        )
    )

    # ------------------------------------------------------------------ #
    # 2. Alter background_grade_metrics
    # ------------------------------------------------------------------ #

    # Drop index that referenced the old string columns
    op.drop_index("ix_bgm_jurisdiction_category", table_name="background_grade_metrics")

    # Drop old plain-string columns (data will be re-seeded via SQL seed script)
    op.drop_column("background_grade_metrics", "emissions_category")
    op.drop_column("background_grade_metrics", "emissions_subcategory")
    op.drop_column("background_grade_metrics", "lifecycle_module_code")

    # Add new FK columns
    op.add_column(
        "background_grade_metrics",
        sa.Column("emissions_category_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "background_grade_metrics",
        sa.Column("emissions_subcategory_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "background_grade_metrics",
        sa.Column("lifecycle_module_code", sa.String(), nullable=True),
    )

    op.create_foreign_key(
        "background_grade_metrics_emissions_category_id_fkey",
        "background_grade_metrics",
        "emissions_categories",
        ["emissions_category_id"],
        ["id"],
    )
    op.create_foreign_key(
        "background_grade_metrics_emissions_subcategory_id_fkey",
        "background_grade_metrics",
        "emissions_categories",
        ["emissions_subcategory_id"],
        ["id"],
    )
    op.create_foreign_key(
        "background_grade_metrics_lifecycle_module_code_fkey",
        "background_grade_metrics",
        "lifecycle_modules",
        ["lifecycle_module_code"],
        ["code"],
    )

    # Recreate jurisdiction-category index on new UUID columns
    op.create_index(
        "ix_bgm_jurisdiction_category",
        "background_grade_metrics",
        ["jurisdiction_id", "emissions_category_id", "emissions_subcategory_id", "emissions_source"],
    )

    # ------------------------------------------------------------------ #
    # 3. Add FK on default_waste_rates.applicable_lifecycle_module_code
    # ------------------------------------------------------------------ #
    op.create_foreign_key(
        "default_waste_rates_applicable_lifecycle_module_code_fkey",
        "default_waste_rates",
        "lifecycle_modules",
        ["applicable_lifecycle_module_code"],
        ["code"],
    )


def downgrade() -> None:
    # Remove FK from default_waste_rates
    op.drop_constraint(
        "default_waste_rates_applicable_lifecycle_module_code_fkey",
        "default_waste_rates",
        type_="foreignkey",
    )

    # Reverse BGM changes
    op.drop_index("ix_bgm_jurisdiction_category", table_name="background_grade_metrics")
    op.drop_constraint(
        "background_grade_metrics_lifecycle_module_code_fkey",
        "background_grade_metrics",
        type_="foreignkey",
    )
    op.drop_constraint(
        "background_grade_metrics_emissions_subcategory_id_fkey",
        "background_grade_metrics",
        type_="foreignkey",
    )
    op.drop_constraint(
        "background_grade_metrics_emissions_category_id_fkey",
        "background_grade_metrics",
        type_="foreignkey",
    )

    op.drop_column("background_grade_metrics", "lifecycle_module_code")
    op.drop_column("background_grade_metrics", "emissions_subcategory_id")
    op.drop_column("background_grade_metrics", "emissions_category_id")

    # Restore old plain-string columns
    op.add_column(
        "background_grade_metrics",
        sa.Column("emissions_category", sa.String(), nullable=True),
    )
    op.add_column(
        "background_grade_metrics",
        sa.Column("emissions_subcategory", sa.String(), nullable=True),
    )
    op.add_column(
        "background_grade_metrics",
        sa.Column("lifecycle_module_code", sa.String(), nullable=True),
    )

    # Restore old index
    op.create_index(
        "ix_bgm_jurisdiction_category",
        "background_grade_metrics",
        ["jurisdiction_id", "emissions_category", "emissions_subcategory", "emissions_source"],
    )

    # Drop lifecycle_modules table
    op.drop_table("lifecycle_modules")

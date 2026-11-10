"""Keep the BAU SCM assumption available on locally migrated views.

Revision ID: cm04_append_bau_scm_view_column
Revises: cm03_bau_concrete_view
"""
from alembic import op


revision = "cm04_append_bau_scm_view_column"
down_revision = "cm03_bau_concrete_view"
branch_labels = None
depends_on = None


# cm03 has already been applied in some databases with an eight-column view.
# CREATE OR REPLACE VIEW may append a new column, but cannot remove or reorder
# existing columns. Keep their existing order and append the compatibility field.
_APPEND_BAU_SCM_COLUMN = r"""
DO $$
BEGIN
    IF to_regclass('public.v_bau_default_concrete_mix') IS NOT NULL
       AND NOT EXISTS (
           SELECT 1
           FROM pg_attribute
           WHERE attrelid = 'public.v_bau_default_concrete_mix'::regclass
             AND attname = 'bau_scm_content_pct'
             AND attnum > 0
             AND NOT attisdropped
       ) THEN
        EXECUTE $view$
            CREATE OR REPLACE VIEW public.v_bau_default_concrete_mix AS
            SELECT
                design.dataset_revision_id,
                strength.strength_mpa,
                design.component_code,
                design.component_label,
                strength.quantity_kg_m3,
                (lower(trim(design.component_code)) = 'total_cementitious_content') AS is_total_cementitious,
                assumptions.default_max_fly_ash_pct,
                design.display_order,
                assumptions.bau_scm_content_pct
            FROM concrete_mix_designs AS design
            CROSS JOIN LATERAL (VALUES
                (20,  design.strength_20_kg_m3),
                (25,  design.strength_25_kg_m3),
                (32,  design.strength_32_kg_m3),
                (40,  design.strength_40_kg_m3),
                (50,  design.strength_50_kg_m3),
                (65,  design.strength_65_kg_m3),
                (80,  design.strength_80_kg_m3),
                (100, design.strength_100_kg_m3)
            ) AS strength(strength_mpa, quantity_kg_m3)
            LEFT JOIN concrete_mix_assumptions AS assumptions
              ON assumptions.dataset_revision_id IS NOT DISTINCT FROM design.dataset_revision_id
             AND assumptions.is_active = TRUE
            WHERE design.is_active = TRUE
        $view$;
    END IF;
END $$;
"""


def upgrade() -> None:
    op.execute(_APPEND_BAU_SCM_COLUMN)


def downgrade() -> None:
    # Intentionally retain this additive compatibility column. Removing a view
    # column would require dropping/recreating the view and could break dependents.
    pass

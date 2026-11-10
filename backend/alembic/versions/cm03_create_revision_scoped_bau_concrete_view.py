"""Create revision-scoped BAU concrete mix view.

Revision ID: cm03_bau_concrete_view
Revises: cm02_normalize_cm_codes
"""
from alembic import op


revision = "cm03_bau_concrete_view"
down_revision = "cm02_normalize_cm_codes"
branch_labels = None
depends_on = None


_CREATE_VIEW = """
CREATE OR REPLACE VIEW public.v_bau_default_concrete_mix AS
SELECT
    design.dataset_revision_id,
    design.component_code,
    design.component_label,
    design.display_order,
    strength.strength_mpa,
    strength.quantity_kg_m3,
    (lower(trim(design.component_code)) = 'total_cementitious_content') AS is_total_cementitious,
    assumptions.bau_scm_content_pct,
    assumptions.default_max_fly_ash_pct
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
"""


def upgrade() -> None:
    op.execute(_CREATE_VIEW)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS public.v_bau_default_concrete_mix")

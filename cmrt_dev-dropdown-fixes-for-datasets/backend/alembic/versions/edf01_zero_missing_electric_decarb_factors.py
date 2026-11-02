"""Fill missing paired electricity factor rows with zero.

Revision ID: edf01_zero_missing_factors
Revises: auslr01_precision
Create Date: 2026-10-28

Source workbooks use a dash for zero in some electricity-factor cells. Those
cells may have been omitted during import. The factor table stores location
and market Scope 2/Scope 3 values in matching revision/jurisdiction/year
dimensions. Where one member of a pair exists, this migration inserts a
missing partner as zero and converts unqualified NULL values in the pair to
zero. Qualified NULL values (for example, qualifier ``D``) are left intact.

The downgrade is intentionally a no-op: after backfill, a zero is valid source
data and cannot safely be distinguished from a zero that was already present.
"""

from alembic import op
import sqlalchemy as sa


revision = "edf01_zero_missing_factors"
down_revision = "auslr01_precision"
branch_labels = None
depends_on = None


_FILL_PAIRED_FACTORS_SQL = """
WITH factor_groups AS (
    SELECT DISTINCT
        dataset_revision_id,
        jurisdiction_id,
        region_id,
        year
    FROM electric_decarb_factors
    WHERE factor_type_code IN (:factor_a, :factor_b)
      AND (
          (:requires_region AND region_id IS NOT NULL)
          OR (NOT :requires_region AND region_id IS NULL)
      )
),
factor_types AS (
    SELECT :factor_a AS factor_type_code
    UNION ALL
    SELECT :factor_b AS factor_type_code
)
INSERT INTO electric_decarb_factors (
    dataset_revision_id,
    factor_type_code,
    jurisdiction_id,
    region_id,
    unit_id,
    year,
    value,
    value_qualifier
)
SELECT
    groups.dataset_revision_id,
    factor_types.factor_type_code,
    groups.jurisdiction_id,
    groups.region_id,
    units.id,
    groups.year,
    0,
    NULL
FROM factor_groups AS groups
CROSS JOIN factor_types
LEFT JOIN units ON units.code = 'tCO2e/MWh'
WHERE NOT EXISTS (
    SELECT 1
    FROM electric_decarb_factors AS existing
    WHERE existing.dataset_revision_id = groups.dataset_revision_id
      AND existing.factor_type_code = factor_types.factor_type_code
      AND existing.jurisdiction_id = groups.jurisdiction_id
      AND existing.year = groups.year
      AND existing.region_id IS NOT DISTINCT FROM groups.region_id
)
ON CONFLICT DO NOTHING;

UPDATE electric_decarb_factors AS target
SET value = 0
WHERE target.factor_type_code IN (:factor_a, :factor_b)
  AND target.value IS NULL
  AND target.value_qualifier IS NULL
  AND (
      (:requires_region AND target.region_id IS NOT NULL)
      OR (NOT :requires_region AND target.region_id IS NULL)
  );
"""


def upgrade() -> None:
    connection = op.get_bind()
    for factor_a, factor_b, requires_region in (
        ("scope2_location", "scope3_location", True),
        ("scope2_market", "scope3_market", False),
    ):
        connection.execute(
            sa.text(_FILL_PAIRED_FACTORS_SQL),
            {
                "factor_a": factor_a,
                "factor_b": factor_b,
                "requires_region": requires_region,
            },
        )


def downgrade() -> None:
    # Intentional: zero is valid source data, and after the upgrade it is not
    # possible to identify which zero rows were synthesized by this migration.
    pass

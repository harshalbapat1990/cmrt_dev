"""Copy published DEFAULT unit conversions into existing scoped revisions.

Revision ID: uc01_backfill_unit_conversions
Revises: edf01_zero_missing_factors
"""

from alembic import op
import sqlalchemy as sa


revision = "uc01_backfill_unit_conversions"
down_revision = "edf01_zero_missing_factors"
branch_labels = None
depends_on = None


BACKFILL_SQL = """
INSERT INTO unit_conversions (
    id,
    dataset_revision_id,
    from_unit_id,
    to_unit_id,
    factor
)
SELECT
    gen_random_uuid(),
    target.id,
    source.from_unit_id,
    source.to_unit_id,
    source.factor
FROM unit_conversions AS source
JOIN (
    SELECT id
    FROM dataset_revisions
    WHERE scope_type = 'DEFAULT'
      AND scope_id IS NULL
      AND status = 'published'
    ORDER BY created_at DESC, id DESC
    LIMIT 1
) AS default_revision
  ON source.dataset_revision_id = default_revision.id
CROSS JOIN dataset_revisions AS target
WHERE target.scope_type <> 'DEFAULT'
  AND NOT EXISTS (
      SELECT 1
      FROM unit_conversions AS existing
      WHERE existing.dataset_revision_id = target.id
        AND existing.from_unit_id = source.from_unit_id
        AND existing.to_unit_id = source.to_unit_id
  )
"""


def upgrade() -> None:
    # Copy the current published DEFAULT conversion set as a baseline into
    # pre-existing ORG/PROJECT revisions. Existing revision-specific pairs
    # remain authoritative, including their direction and factor.
    op.execute(sa.text(BACKFILL_SQL))


def downgrade() -> None:
    # Copied rows are indistinguishable from conversion rows created directly
    # in a revision, so deleting them could destroy user-authored data.
    pass

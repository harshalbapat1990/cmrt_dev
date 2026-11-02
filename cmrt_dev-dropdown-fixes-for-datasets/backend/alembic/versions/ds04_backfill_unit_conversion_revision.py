"""Attach legacy global unit conversions to the published default revision.

Revision ID: ds04_unit_conversion_revision
Revises: ds03_density_record_keys
"""
from alembic import op
import sqlalchemy as sa


revision = "ds04_unit_conversion_revision"
down_revision = "ds03_density_record_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # dt01 added the nullable revision column but left existing global rows
    # unassigned. Put them on the current published DEFAULT branch so scoped
    # reads and future branch copies include them.
    # If a pair already has a DEFAULT-branch row, keep that explicit branch
    # value and remove its older revision-less duplicate before assigning the
    # remaining legacy rows (the revision-scoped unique index is partial).
    op.execute(sa.text("""
        DELETE FROM unit_conversions legacy
        USING unit_conversions scoped,
              (
                SELECT id FROM dataset_revisions
                WHERE scope_type = 'DEFAULT'
                  AND scope_id IS NULL
                  AND status = 'published'
                ORDER BY created_at DESC
                LIMIT 1
              ) default_revision
        WHERE legacy.dataset_revision_id IS NULL
          AND scoped.dataset_revision_id = default_revision.id
          AND legacy.from_unit_id = scoped.from_unit_id
          AND legacy.to_unit_id = scoped.to_unit_id
    """))
    op.execute(sa.text("""
        UPDATE unit_conversions
        SET dataset_revision_id = (
            SELECT id
            FROM dataset_revisions
            WHERE scope_type = 'DEFAULT'
              AND scope_id IS NULL
              AND status = 'published'
            ORDER BY created_at DESC
            LIMIT 1
        )
        WHERE dataset_revision_id IS NULL
          AND EXISTS (
            SELECT 1
            FROM dataset_revisions
            WHERE scope_type = 'DEFAULT'
              AND scope_id IS NULL
              AND status = 'published'
        )
    """))


def downgrade() -> None:
    # Preserve assigned rows; a downgrade cannot reliably distinguish legacy
    # rows from rows created in the DEFAULT branch after the upgrade.
    pass

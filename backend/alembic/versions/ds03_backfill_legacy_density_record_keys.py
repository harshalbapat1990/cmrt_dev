"""Backfill the empty record keys created for existing density rows.

Revision ID: ds03_density_record_keys
Revises: ds02_revision_legacy_tables
"""
from alembic import op
import sqlalchemy as sa


revision = "ds03_density_record_keys"
down_revision = "ds02_revision_legacy_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The earlier record_key migration used an empty server default to satisfy
    # NOT NULL for existing rows. Their UUID is a stable unique fallback key.
    op.execute(sa.text("""
        UPDATE densities
        SET record_key = 'legacy:' || id::text
        WHERE record_key IS NULL OR btrim(record_key) = ''
    """))


def downgrade() -> None:
    # Do not erase record keys because some may have been edited after upgrade.
    pass

"""add_recurring_to_project_stage_enum

Revision ID: r1_add_recurring_stage_enum
Revises: eeaf4dbb6119
Create Date: 2026-05-11 00:00:00.000000

Adds RECURRING to the project_stage PostgreSQL enum so contractor/maintenance
projects can have a dedicated stage instance for storing activity data.
"""
from alembic import op

revision = "r1_add_recurring_stage_enum"
down_revision = "eeaf4dbb6119"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL does not allow removing enum values, so only downgrade is a no-op.
    op.execute("ALTER TYPE project_stage ADD VALUE IF NOT EXISTS 'RECURRING';")


def downgrade() -> None:
    # Removing enum values requires a full type rebuild; skip for safety.
    pass

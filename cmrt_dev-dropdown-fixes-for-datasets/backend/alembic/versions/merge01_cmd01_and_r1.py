"""merge cmd01_concrete_mix_designs and r1_add_recurring_stage_enum

Revision ID: merge01_cmd01_and_r1
Revises: cmd01_concrete_mix_designs, r1_add_recurring_stage_enum
Create Date: 2026-05-11 00:00:00.000000

Merge migration to reunite the concrete-mix-designs branch and the
recurring-stage-enum branch into a single head.
"""
from alembic import op

revision = "merge01_cmd01_and_r1"
down_revision = ("cmd01_concrete_mix_designs", "r1_add_recurring_stage_enum")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

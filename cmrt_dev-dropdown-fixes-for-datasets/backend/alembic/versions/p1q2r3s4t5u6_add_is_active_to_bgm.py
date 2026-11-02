"""add_is_active_to_bgm

Revision ID: p1q2r3s4t5u6
Revises: o1p2q3r4s5t6
Create Date: 2026-03-18 00:00:00.000000

Adds is_active boolean column to background_grade_metrics so that the
supersede pattern can be used for edits, preserving a full audit trail.
Superseded (inactive) rows are soft-deleted with is_active = FALSE while
the replacement row gets a fresh id with is_active = TRUE.
"""

from alembic import op
import sqlalchemy as sa

revision = "p1q2r3s4t5u6"
down_revision = "o1p2q3r4s5t6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "background_grade_metrics",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    # Partial index so the main list query (WHERE is_active = TRUE) stays fast
    op.create_index(
        "ix_bgm_active_factor_set_grade",
        "background_grade_metrics",
        ["factor_set_id", "grade_id"],
        postgresql_where=sa.text("is_active = TRUE"),
    )


def downgrade() -> None:
    op.drop_index("ix_bgm_active_factor_set_grade", table_name="background_grade_metrics")
    op.drop_column("background_grade_metrics", "is_active")

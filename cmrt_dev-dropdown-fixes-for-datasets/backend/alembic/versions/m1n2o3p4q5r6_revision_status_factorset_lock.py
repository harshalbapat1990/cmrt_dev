"""
Add lifecycle status to dataset_revisions and is_locked/created_by/created_at
to emissions_factor_sets.

Scenario coverage:
  - 1.1 / 1.2 / 1.3 / 1.4  Dataset Revision lifecycle (status field)
  - 2.3                      Lock Factor Set (is_locked field)
"""
from alembic import op
import sqlalchemy as sa

revision = "m1n2o3p4q5r6"
down_revision = "l1m2n3o4p5q6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── dataset_revisions: add status column ──────────────────────────────
    op.add_column(
        "dataset_revisions",
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="draft",
        ),
    )
    # Existing rows are already "draft" by virtue of the server_default.

    # ── emissions_factor_sets: add is_locked, created_by, created_at ─────
    op.add_column(
        "emissions_factor_sets",
        sa.Column(
            "is_locked",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "emissions_factor_sets",
        sa.Column(
            "created_by",
            sa.UUID(),
            nullable=True,
        ),
    )
    op.add_column(
        "emissions_factor_sets",
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_foreign_key(
        "emissions_factor_sets_created_by_fkey",
        "emissions_factor_sets",
        "users",
        ["created_by"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "emissions_factor_sets_created_by_fkey",
        "emissions_factor_sets",
        type_="foreignkey",
    )
    op.drop_column("emissions_factor_sets", "created_at")
    op.drop_column("emissions_factor_sets", "created_by")
    op.drop_column("emissions_factor_sets", "is_locked")
    op.drop_column("dataset_revisions", "status")

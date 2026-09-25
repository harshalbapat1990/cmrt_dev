"""
Add approval_status / approved_by / approved_at to project_stage_instances.

Scenario coverage:
  - 9.1  Stage Technical Approval
  - 9.2  Final Approval
  - 9.3  Re-open Stage
"""
from alembic import op
import sqlalchemy as sa

revision = "n1o2p3q4r5s6"
down_revision = "m1n2o3p4q5r6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "project_stage_instances",
        sa.Column(
            "approval_status",
            sa.String(20),
            nullable=False,
            server_default="open",
        ),
    )
    op.add_column(
        "project_stage_instances",
        sa.Column(
            "approved_by",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "project_stage_instances",
        sa.Column("approved_at", sa.TIMESTAMP(), nullable=True),
    )
    op.create_foreign_key(
        "project_stage_instances_approved_by_fkey",
        "project_stage_instances",
        "users",
        ["approved_by"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "project_stage_instances_approved_by_fkey",
        "project_stage_instances",
        type_="foreignkey",
    )
    op.drop_column("project_stage_instances", "approved_at")
    op.drop_column("project_stage_instances", "approved_by")
    op.drop_column("project_stage_instances", "approval_status")

"""stage_approval_workflow_v2

Revision ID: g7h8i9j0k1l2
Revises: f1a2b3c4d5e6
Create Date: 2026-04-02 00:00:00.000000

Adds submitted_by / submitted_at / current_justification to project_stage_instances,
and creates the stage_approval_events table for a full audit trail.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "g7h8i9j0k1l2"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Extend project_stage_instances ────────────────────────────────────
    op.add_column(
        "project_stage_instances",
        sa.Column("submitted_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "project_stage_instances",
        sa.Column("submitted_at", sa.TIMESTAMP(timezone=False), nullable=True),
    )
    op.add_column(
        "project_stage_instances",
        sa.Column("current_justification", sa.Text(), nullable=True),
    )
    op.create_foreign_key(
        "fk_psi_submitted_by_users",
        "project_stage_instances",
        "users",
        ["submitted_by"],
        ["id"],
        ondelete="SET NULL",
    )

    # ── 2. Create stage_approval_events ──────────────────────────────────────
    op.create_table(
        "stage_approval_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "stage_instance_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("project_stage_instances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("project.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column(
            "performed_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "performed_at",
            sa.TIMESTAMP(timezone=False),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("justification", sa.Text(), nullable=True),
        sa.Column("from_status", sa.String(20), nullable=True),
        sa.Column("to_status", sa.String(20), nullable=True),
        sa.Column("report_number", sa.Integer(), nullable=True),
    )

    op.create_index(
        "ix_stage_approval_events_instance_performed_at",
        "stage_approval_events",
        ["stage_instance_id", "performed_at"],
    )
    op.create_index(
        "ix_stage_approval_events_project_type_performed_at",
        "stage_approval_events",
        ["project_id", "event_type", "performed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_stage_approval_events_project_type_performed_at", "stage_approval_events")
    op.drop_index("ix_stage_approval_events_instance_performed_at", "stage_approval_events")
    op.drop_table("stage_approval_events")
    op.drop_constraint("fk_psi_submitted_by_users", "project_stage_instances", type_="foreignkey")
    op.drop_column("project_stage_instances", "current_justification")
    op.drop_column("project_stage_instances", "submitted_at")
    op.drop_column("project_stage_instances", "submitted_by")

"""add project_mitigations and activity_data.project_mitigation_id

Revision ID: pm01_add_pm
Revises: 9ef9cc7aa311
Create Date: 2026-05-01

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "pm01_add_pm"
down_revision: Union[str, Sequence[str], None] = "9ef9cc7aa311"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_mitigations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "project_stage_instance_id",
            UUID(as_uuid=True),
            sa.ForeignKey("project_stage_instances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_option_id",
            UUID(as_uuid=True),
            sa.ForeignKey("project_options.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("submission_stage", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("mitigation_type", sa.String(length=32), nullable=False),
        sa.Column("lifecycle_phase", sa.String(length=64), nullable=False),
        sa.Column("lifecycle_phase_label", sa.String(length=128), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("group_label", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=False), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=False), nullable=True),
    )
    op.create_index("ix_project_mitigations_stage_option", "project_mitigations", ["project_stage_instance_id", "project_option_id"])

    op.add_column(
        "activity_data",
        sa.Column(
            "project_mitigation_id",
            UUID(as_uuid=True),
            sa.ForeignKey("project_mitigations.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_index("ix_activity_data_project_mitigation_id", "activity_data", ["project_mitigation_id"])


def downgrade() -> None:
    op.drop_index("ix_activity_data_project_mitigation_id", table_name="activity_data")
    op.drop_column("activity_data", "project_mitigation_id")
    op.drop_index("ix_project_mitigations_stage_option", table_name="project_mitigations")
    op.drop_table("project_mitigations")
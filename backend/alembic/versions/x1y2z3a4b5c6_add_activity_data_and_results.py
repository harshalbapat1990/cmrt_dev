"""add_activity_data_and_results

Revision ID: x1y2z3a4b5c6
Revises: w1x2y3z4a5b6
Create Date: 2026-03-28 00:00:00.000000

Creates the three core data-entry storage tables:
  - project_options  (Business Case option records)
  - activity_data    (all user-entered rows)
  - emissions_results (calculated tCO2e per activity row)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "x1y2z3a4b5c6"
down_revision: Union[str, Sequence[str], None] = "w1x2y3z4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. project_options ──────────────────────────────────────────────────
    op.create_table(
        "project_options",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stage_instance_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("project_stage_instances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("option_number", sa.Integer, nullable=False),
        sa.Column("label", sa.String, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=False), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("project_id", "stage_instance_id", "option_number", name="project_options_project_stage_option_key"),
    )

    # ── 2. activity_data ────────────────────────────────────────────────────
    op.create_table(
        "activity_data",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_stage_instance_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("project_stage_instances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_option_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("project_options.id", ondelete="SET NULL"), nullable=True),
        sa.Column("component_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metric_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("background_grade_metrics.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("quantity", sa.Numeric, nullable=False),
        sa.Column("unit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("units.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("ui_table_key", sa.String(30), nullable=False),
        sa.Column("lifecycle_module_code", sa.String, sa.ForeignKey("lifecycle_modules.code"), nullable=True),
        sa.Column("extra_fields", postgresql.JSONB, nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=False), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=False), nullable=True),
    )
    op.create_index("ix_activity_data_stage_table", "activity_data", ["project_stage_instance_id", "ui_table_key"])
    op.create_index("ix_activity_data_project_id", "activity_data", ["project_id"])

    # ── 3. emissions_results ────────────────────────────────────────────────
    op.create_table(
        "emissions_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_stage_instance_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("project_stage_instances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("activity_data_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("activity_data.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lifecycle_module_code", sa.String, sa.ForeignKey("lifecycle_modules.code"), nullable=True),
        sa.Column("value", sa.Numeric, nullable=False),
        sa.Column("unit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("units.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=False), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("activity_data_id", "lifecycle_module_code", name="emissions_results_activity_lifecycle_key"),
    )


def downgrade() -> None:
    op.drop_table("emissions_results")
    op.drop_index("ix_activity_data_stage_table", table_name="activity_data")
    op.drop_index("ix_activity_data_project_id", table_name="activity_data")
    op.drop_table("activity_data")
    op.drop_table("project_options")

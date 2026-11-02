"""add_report_number_to_project_options

Revision ID: aa2bb3cc4dd5
Revises: z1a2b3c4d5e6
Create Date: 2026-04-01 00:00:00.000000

Adds report_number and is_default columns to project_options.
report_number groups sub-options within a stage report slot
(driven by num_reports_required).  is_default marks the canonical
base-case sub-option for a given report.

Data migration: re-interprets existing rows (previously one row per
"Option N") as report-level slots — each becomes report_number=N,
option_number=1, is_default=True.  The existing UUIDs in
activity_data.project_option_id remain valid.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "aa2bb3cc4dd5"
down_revision: Union[str, Sequence[str], None] = "z1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add new columns with permissive defaults so existing rows satisfy NOT NULL
    op.add_column(
        "project_options",
        sa.Column("report_number", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "project_options",
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="true"),
    )

    # 2. Drop old unique constraint BEFORE the data migration so setting
    #    multiple rows to option_number=1 doesn't violate it
    op.drop_constraint(
        "project_options_project_stage_option_key",
        "project_options",
        type_="unique",
    )

    # 3. Data migration: treat existing option_number as the report_number,
    #    reset option_number to 1 (single default sub-option per report)
    op.execute(
        """
        UPDATE project_options
        SET report_number = option_number,
            option_number = 1,
            is_default    = TRUE
        """
    )

    # 4. Add new unique constraint covering (project_id, stage_instance_id, report_number, option_number)
    op.create_unique_constraint(
        "project_options_project_stage_report_option_key",
        "project_options",
        ["project_id", "stage_instance_id", "report_number", "option_number"],
    )

    # 5. Remove server defaults (application layer owns these now)
    op.alter_column("project_options", "report_number", server_default=None)
    op.alter_column("project_options", "is_default", server_default=None)


def downgrade() -> None:
    op.drop_constraint(
        "project_options_project_stage_report_option_key",
        "project_options",
        type_="unique",
    )

    # Reverse data migration: restore option_number from report_number
    op.execute(
        """
        UPDATE project_options
        SET option_number = report_number
        """
    )

    op.create_unique_constraint(
        "project_options_project_stage_option_key",
        "project_options",
        ["project_id", "stage_instance_id", "option_number"],
    )

    op.drop_column("project_options", "is_default")
    op.drop_column("project_options", "report_number")

from alembic import op

revision = 'cp02_fix_period_unique'
down_revision = 'cp01_period_workflow'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        'project_reporting_submission_project_id_period_label_key',
        'project_reporting_submission',
        type_='unique',
    )

    op.execute(
        """
        CREATE UNIQUE INDEX uq_prs_legacy_period_label
        ON project_reporting_submission (project_id, period_label)
        WHERE stage_instance_id IS NULL
        """
    )

    op.execute(
        """
        CREATE UNIQUE INDEX uq_prs_construction_period_label
        ON project_reporting_submission (stage_instance_id, period_label)
        WHERE stage_instance_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_prs_legacy_period_label")
    op.execute("DROP INDEX IF EXISTS uq_prs_construction_period_label")
    op.create_unique_constraint(
        'project_reporting_submission_project_id_period_label_key',
        'project_reporting_submission',
        ['project_id', 'period_label'],
    )

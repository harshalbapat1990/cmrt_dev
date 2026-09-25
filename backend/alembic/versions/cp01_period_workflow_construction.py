from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'cp01_period_workflow'
down_revision = '8c9d0e1f2g3h'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'project_reporting_submission',
        sa.Column('status', sa.String(30), nullable=False, server_default='in_progress'),
    )
    op.add_column(
        'project_reporting_submission',
        sa.Column('stage_instance_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        'project_reporting_submission',
        sa.Column('submitted_by', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        'project_reporting_submission',
        sa.Column('submitted_at', sa.TIMESTAMP(), nullable=True),
    )
    op.add_column(
        'project_reporting_submission',
        sa.Column('decision_by', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        'project_reporting_submission',
        sa.Column('decision_at', sa.TIMESTAMP(), nullable=True),
    )
    op.add_column(
        'project_reporting_submission',
        sa.Column('rejection_reason', sa.Text(), nullable=True),
    )
    op.add_column(
        'project_reporting_submission',
        sa.Column('reopen_requested_by', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        'project_reporting_submission',
        sa.Column('reopen_requested_at', sa.TIMESTAMP(), nullable=True),
    )
    op.add_column(
        'project_reporting_submission',
        sa.Column('reopen_reason', sa.Text(), nullable=True),
    )

    op.execute(
        "UPDATE project_reporting_submission SET status = 'approved' WHERE is_open = false"
    )

    op.create_foreign_key(
        'fk_prs_stage_instance',
        'project_reporting_submission',
        'project_stage_instances',
        ['stage_instance_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        'fk_prs_submitted_by',
        'project_reporting_submission',
        'users',
        ['submitted_by'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        'fk_prs_decision_by',
        'project_reporting_submission',
        'users',
        ['decision_by'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        'fk_prs_reopen_requested_by',
        'project_reporting_submission',
        'users',
        ['reopen_requested_by'],
        ['id'],
        ondelete='SET NULL',
    )

    op.drop_column('project_reporting_submission', 'is_open')

    op.add_column(
        'activity_data',
        sa.Column('submission_period_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_activity_data_period',
        'activity_data',
        'project_reporting_submission',
        ['submission_period_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index(
        'ix_activity_data_period_id',
        'activity_data',
        ['submission_period_id'],
    )

    op.add_column(
        'stage_approval_events',
        sa.Column('submission_period_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_stage_events_period',
        'stage_approval_events',
        'project_reporting_submission',
        ['submission_period_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_index(
        'ix_stage_approval_events_period_id',
        'stage_approval_events',
        ['submission_period_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_stage_approval_events_period_id', table_name='stage_approval_events')
    op.drop_constraint('fk_stage_events_period', 'stage_approval_events', type_='foreignkey')
    op.drop_column('stage_approval_events', 'submission_period_id')

    op.drop_index('ix_activity_data_period_id', table_name='activity_data')
    op.drop_constraint('fk_activity_data_period', 'activity_data', type_='foreignkey')
    op.drop_column('activity_data', 'submission_period_id')

    op.add_column(
        'project_reporting_submission',
        sa.Column('is_open', sa.Boolean(), nullable=True, server_default=sa.true()),
    )
    op.execute(
        "UPDATE project_reporting_submission SET is_open = (status != 'approved')"
    )
    op.alter_column('project_reporting_submission', 'is_open', nullable=False)

    op.drop_constraint('fk_prs_reopen_requested_by', 'project_reporting_submission', type_='foreignkey')
    op.drop_constraint('fk_prs_decision_by', 'project_reporting_submission', type_='foreignkey')
    op.drop_constraint('fk_prs_submitted_by', 'project_reporting_submission', type_='foreignkey')
    op.drop_constraint('fk_prs_stage_instance', 'project_reporting_submission', type_='foreignkey')

    op.drop_column('project_reporting_submission', 'reopen_reason')
    op.drop_column('project_reporting_submission', 'reopen_requested_at')
    op.drop_column('project_reporting_submission', 'reopen_requested_by')
    op.drop_column('project_reporting_submission', 'rejection_reason')
    op.drop_column('project_reporting_submission', 'decision_at')
    op.drop_column('project_reporting_submission', 'decision_by')
    op.drop_column('project_reporting_submission', 'submitted_at')
    op.drop_column('project_reporting_submission', 'submitted_by')
    op.drop_column('project_reporting_submission', 'stage_instance_id')
    op.drop_column('project_reporting_submission', 'status')

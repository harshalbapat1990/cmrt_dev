"""no_factor_sets_delta_architecture

Revision ID: 9a8b7c6d5e4f
Revises: 71d7b6ad8d52
Create Date: 2025-04-19 00:00:00.000000

Eliminates emissions_factor_sets entirely and implements delta-based
PROJECT->ORG->DEFAULT resolution on DatasetRevision directly.
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9a8b7c6d5e4f'
down_revision: Union[str, None] = '71d7b6ad8d52'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add parent_revision_id to dataset_revisions (self-referential FK)
    op.add_column(
        'dataset_revisions',
        sa.Column('parent_revision_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_dataset_revisions_parent_id',
        'dataset_revisions', 'dataset_revisions',
        ['parent_revision_id'], ['id'],
        ondelete='SET NULL',
    )

    # 2. Add dataset_revision_id to background_grade_metrics
    op.add_column(
        'background_grade_metrics',
        sa.Column('dataset_revision_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_bgm_dataset_revision_id',
        'background_grade_metrics', 'dataset_revisions',
        ['dataset_revision_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_index(
        'ix_background_grade_metrics_dataset_revision_id',
        'background_grade_metrics',
        ['dataset_revision_id'],
    )

    # 3. Migrate data: set dataset_revision_id on bgm rows from their factor_set's revision
    op.execute("""
        UPDATE background_grade_metrics bgm
        SET dataset_revision_id = efs.dataset_revision_id
        FROM emissions_factor_sets efs
        WHERE bgm.factor_set_id = efs.id
          AND efs.dataset_revision_id IS NOT NULL
    """)

    # 4. Drop factor_set_id FK constraint then column from background_grade_metrics
    op.drop_constraint(
        'background_grade_metrics_factor_set_id_fkey',
        'background_grade_metrics',
        type_='foreignkey',
    )
    op.drop_column('background_grade_metrics', 'factor_set_id')

    # 5. Alter activity_data: drop metric_id, add dataset_revision_id + metric_natural_key
    op.drop_constraint(
        'fk__activity_data__metric_id__background_grade_metrics',
        'activity_data',
        type_='foreignkey',
    )
    op.drop_column('activity_data', 'metric_id')
    op.add_column(
        'activity_data',
        sa.Column('dataset_revision_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_activity_data_dataset_revision_id',
        'activity_data', 'dataset_revisions',
        ['dataset_revision_id'], ['id'],
        ondelete='SET NULL',
    )
    op.add_column(
        'activity_data',
        sa.Column('metric_natural_key', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    # 6. Alter dataset_revision_changes: drop metric_id FK+col, add metric_natural_key
    op.drop_constraint(
        'dataset_revision_changes_metric_id_fkey',
        'dataset_revision_changes',
        type_='foreignkey',
    )
    op.drop_column('dataset_revision_changes', 'metric_id')
    op.add_column(
        'dataset_revision_changes',
        sa.Column(
            'metric_natural_key',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='{}',
        ),
    )

    # 7. Drop emissions_factor_sets table (CASCADE handles any remaining FKs)
    op.execute('DROP TABLE IF EXISTS emissions_factor_sets CASCADE')


def downgrade() -> None:
    # Recreate emissions_factor_sets table
    op.create_table(
        'emissions_factor_sets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('version', sa.String(50), nullable=True),
        sa.Column('source', sa.String(255), nullable=True),
        sa.Column('jurisdiction_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('dataset_revision_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('valid_from', sa.Date(), nullable=True),
        sa.Column('valid_to', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_locked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    # Restore dataset_revision_changes.metric_id
    op.drop_column('dataset_revision_changes', 'metric_natural_key')
    op.add_column(
        'dataset_revision_changes',
        sa.Column('metric_id', postgresql.UUID(as_uuid=True), nullable=True),
    )

    # Restore activity_data.metric_id
    op.drop_constraint('fk_activity_data_dataset_revision_id', 'activity_data', type_='foreignkey')
    op.drop_column('activity_data', 'metric_natural_key')
    op.drop_column('activity_data', 'dataset_revision_id')
    op.add_column(
        'activity_data',
        sa.Column('metric_id', postgresql.UUID(as_uuid=True), nullable=True),
    )

    # Restore background_grade_metrics.factor_set_id
    op.drop_index('ix_background_grade_metrics_dataset_revision_id', table_name='background_grade_metrics')
    op.drop_constraint('fk_bgm_dataset_revision_id', 'background_grade_metrics', type_='foreignkey')
    op.drop_column('background_grade_metrics', 'dataset_revision_id')
    op.add_column(
        'background_grade_metrics',
        sa.Column('factor_set_id', postgresql.UUID(as_uuid=True), nullable=True),
    )

    # Remove parent_revision_id from dataset_revisions
    op.drop_constraint('fk_dataset_revisions_parent_id', 'dataset_revisions', type_='foreignkey')
    op.drop_column('dataset_revisions', 'parent_revision_id')

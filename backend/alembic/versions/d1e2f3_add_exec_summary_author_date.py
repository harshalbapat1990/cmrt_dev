"""add exec_summary_author and exec_summary_date to project_options and project_reporting_submission

Revision ID: d1e2f3_exec_summary_author
Revises: prjboundary01
Create Date: 2026-04-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'd1e2f3_exec_summary_author'
down_revision: Union[str, None] = 'prjboundary01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('project_options', sa.Column('exec_summary_author', sa.Text(), nullable=True))
    op.add_column('project_options', sa.Column('exec_summary_date', sa.TIMESTAMP(), nullable=True))
    op.add_column('project_reporting_submission', sa.Column('exec_summary_author', sa.Text(), nullable=True))
    op.add_column('project_reporting_submission', sa.Column('exec_summary_date', sa.TIMESTAMP(), nullable=True))


def downgrade() -> None:
    op.drop_column('project_reporting_submission', 'exec_summary_date')
    op.drop_column('project_reporting_submission', 'exec_summary_author')
    op.drop_column('project_options', 'exec_summary_date')
    op.drop_column('project_options', 'exec_summary_author')

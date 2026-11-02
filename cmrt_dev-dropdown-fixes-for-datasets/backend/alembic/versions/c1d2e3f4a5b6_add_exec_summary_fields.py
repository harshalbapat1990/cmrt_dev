"""add exec_summary fields to project_options and project_reporting_submission

Revision ID: c1d2e3f4a5b6
Revises: 0c6e721b420b
Create Date: 2026-04-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, None] = '0c6e721b420b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('project_options', sa.Column('exec_summary', sa.Text(), nullable=True))
    op.add_column('project_reporting_submission', sa.Column('exec_summary', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('project_reporting_submission', 'exec_summary')
    op.drop_column('project_options', 'exec_summary')

"""add_approval_status_to_project_options

Revision ID: b1c2d3e4f5a6
Revises: a18ee7d99188
Create Date: 2026-04-11 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b1c2d3e4f5a6'
down_revision = 'a18ee7d99188'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'project_options',
        sa.Column('approval_status', sa.String(30), nullable=False, server_default='draft'),
    )
    op.add_column(
        'project_options',
        sa.Column('current_justification', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('project_options', 'current_justification')
    op.drop_column('project_options', 'approval_status')

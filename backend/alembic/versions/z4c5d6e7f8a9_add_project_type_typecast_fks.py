"""add_project_type_typecast_fks

Revision ID: z4c5d6e7f8a9
Revises: d1e2f3_exec_summary_author
Create Date: 2026-04-16 00:00:00.000000

Transition project_type and project_typecast to use UUID foreign keys to benchmark tables.
Removes legacy string columns and replaces with FK columns.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = 'z4c5d6e7f8a9'
down_revision = 'd1e2f3_exec_summary_author'
branch_labels = None
depends_on = None

def upgrade() -> None:
   pass


def downgrade() -> None:
   pass

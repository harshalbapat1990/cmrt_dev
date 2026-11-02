"""widen activity_data.ui_table_key for mitigation substitution keys

Mitigation substitution legs use keys such as
``useB1G2-mitigation-subst-replaced`` (34 chars), which exceed VARCHAR(30).

Revision ID: a9b8c7d6e5f4
Revises: merge01_cmd01_and_r1
Create Date: 2026-05-11

"""

from alembic import op
import sqlalchemy as sa

revision = "a9b8c7d6e5f4"
down_revision = "merge01_cmd01_and_r1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "activity_data",
        "ui_table_key",
        type_=sa.String(64),
        existing_type=sa.String(30),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "activity_data",
        "ui_table_key",
        type_=sa.String(30),
        existing_type=sa.String(64),
        existing_nullable=False,
    )

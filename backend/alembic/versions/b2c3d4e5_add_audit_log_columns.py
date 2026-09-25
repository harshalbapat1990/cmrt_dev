"""add audit log extended context columns

Revision ID: b2c3d4e5
Revises: 1a25accd72ec
Create Date: 2025-07-23

"""
from alembic import op
import sqlalchemy as sa

revision = "b2c3d4e5"
down_revision = "1a25accd72ec"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "audit_logs",
        sa.Column("performed_by_email", sa.String(255), nullable=True),
    )
    op.add_column(
        "audit_logs",
        sa.Column("performed_by_org_name", sa.String(255), nullable=True),
    )
    op.add_column(
        "audit_logs",
        sa.Column("entity_name", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("audit_logs", "entity_name")
    op.drop_column("audit_logs", "performed_by_org_name")
    op.drop_column("audit_logs", "performed_by_email")

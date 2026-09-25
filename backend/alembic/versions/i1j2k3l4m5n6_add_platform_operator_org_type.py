"""i1j2k3l4m5n6_add_platform_operator_org_type.py

Revision ID: i1j2k3l4m5n6
Revises: h1i2j3k4l5m6
Create Date: 2026-03-12

Changes
-------
1.  organization_type enum: add 'PLATFORM_OPERATOR' value.

    PLATFORM_OPERATOR orgs represent internal platform operators (e.g. Austroads).
    Users who register against a PLATFORM_OPERATOR org submit a SUPER_ADMIN access
    request instead of an ORG_ADMIN request.  An existing SUPER_ADMIN must approve
    before the new user gains platform-level access.

Note: ALTER TYPE ... ADD VALUE is transactional in PostgreSQL 12+.  This
      migration assumes PostgreSQL 12 or later (Azure Flexible Server default).
"""

from alembic import op

# revision identifiers
revision = "i1j2k3l4m5n6"
down_revision = "h1i2j3k4l5m6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE organization_type ADD VALUE IF NOT EXISTS 'PLATFORM_OPERATOR'"
    )


def downgrade() -> None:
    # PostgreSQL does not support removing a value from an enum without
    # recreating the type.  Downgrade is intentionally a no-op; remove the
    # value manually if strictly required.
    pass

"""add user_roles performance indexes

Revision ID: k1l2m3n4o5p6
Revises: j1k2l3m4n5o6
Create Date: 2026-03-16

Adds indexes on user_roles that are hit on every authenticated request
by the RBAC helpers (get_effective_role_names, get_org_scoped_role_names, etc.).
"""

from alembic import op

revision = "k1l2m3n4o5p6"
down_revision = "j1k2l3m4n5o6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Primary RBAC lookup: filter by user + active flag
    op.create_index(
        "ix_user_roles_user_id_is_active",
        "user_roles",
        ["user_id", "is_active"],
    )
    # Scope-type filter on top of the above (used in most WHERE clauses)
    op.create_index(
        "ix_user_roles_user_id_scope_type",
        "user_roles",
        ["user_id", "scope_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_roles_user_id_scope_type", table_name="user_roles")
    op.drop_index("ix_user_roles_user_id_is_active", table_name="user_roles")

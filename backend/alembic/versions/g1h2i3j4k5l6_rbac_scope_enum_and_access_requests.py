"""g1h2i3j4k5l6_rbac_scope_enum_and_access_requests.py

Revision ID: g1h2i3j4k5l6
Revises: dbfef4e7be4e
Create Date: 2026-03-11

Changes
-------
1.  user_roles.scope_type:
    - Made NOT NULL with default 'GLOBAL'
    - Added CHECK constraint: must be one of GLOBAL/ORGANISATION/PROJECT/STAGE
    - Replaced the multi-column UNIQUE with a partial expression index that
      handles the NULL scope_id for GLOBAL rows correctly.

2.  New table: access_requests
    Generic request/approval workflow for Org Admin promotions and any future
    access requests (project/stage roles, report-reopen, etc.).
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers
revision = "g1h2i3j4k5l6"
down_revision = "dbfef4e7be4e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # 1. user_roles – scope_type normalisation                            #
    # ------------------------------------------------------------------ #

    # Set default value for existing NULL scope_type rows → 'GLOBAL'
    op.execute("UPDATE user_roles SET scope_type = 'GLOBAL' WHERE scope_type IS NULL")

    # Normalise any legacy / non-canonical scope_type values → 'GLOBAL'
    op.execute(
        "UPDATE user_roles SET scope_type = 'GLOBAL' "
        "WHERE scope_type NOT IN ('GLOBAL', 'ORGANISATION', 'PROJECT', 'STAGE')"
    )

    # Make scope_type NOT NULL
    op.alter_column("user_roles", "scope_type", nullable=False, server_default="GLOBAL")

    # Add CHECK constraint for canonical scope values
    op.create_check_constraint(
        "ck_user_roles_scope_type",
        "user_roles",
        "scope_type IN ('GLOBAL', 'ORGANISATION', 'PROJECT', 'STAGE')",
    )

    # Drop the existing unique constraint (it doesn't handle NULL scope_id well)
    op.drop_constraint(
        "user_roles_user_id_role_id_scope_type_scope_id_key",
        "user_roles",
        type_="unique",
    )

    # Re-create as two partial unique indexes:
    #   a) for GLOBAL roles (scope_id IS NULL) – one row per (user, role, GLOBAL)
    #   b) for scoped roles (scope_id IS NOT NULL) – one row per (user, role, type, id)
    op.execute(
        """
        CREATE UNIQUE INDEX uq_user_roles_global
        ON user_roles (user_id, role_id, scope_type)
        WHERE scope_id IS NULL
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_user_roles_scoped
        ON user_roles (user_id, role_id, scope_type, scope_id)
        WHERE scope_id IS NOT NULL
        """
    )

    # ------------------------------------------------------------------ #
    # 2. access_requests table                                            #
    # ------------------------------------------------------------------ #
    op.create_table(
        "access_requests",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        # Type of request (open-ended string; add rows, never change schema)
        sa.Column("request_type", sa.String(50), nullable=False),

        # Status machine
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),

        # Who raised the request and on whose behalf
        sa.Column(
            "requester_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "target_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),

        # Role being requested (nullable for non-role requests e.g. report reopen)
        sa.Column(
            "requested_role_id",
            UUID(as_uuid=True),
            sa.ForeignKey("roles.id"),
            nullable=True,
        ),

        # Scope (same semantics as user_roles)
        sa.Column("scope_type", sa.String(20), nullable=False, server_default="GLOBAL"),
        sa.Column("scope_id", UUID(as_uuid=True), nullable=True),

        # Denormalised for fast filtering (avoids joins on list endpoints)
        sa.Column(
            "organisation_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organization.id"),
            nullable=True,
        ),
        sa.Column(
            "project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("project.id"),
            nullable=True,
        ),

        # Why the request was made (free-text from requester)
        sa.Column("reason", sa.Text, nullable=True),

        # Decision fields (populated on approve/reject)
        sa.Column("decision_note", sa.Text, nullable=True),
        sa.Column(
            "reviewed_by_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("reviewed_at", sa.TIMESTAMP(timezone=False), nullable=True),

        # Timestamps
        sa.Column(
            "created_on",
            sa.TIMESTAMP(timezone=False),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_on", sa.TIMESTAMP(timezone=False), nullable=True),

        # Extensible payload for future request categories
        sa.Column("metadata", JSONB, nullable=True),

        # Constraints
        sa.CheckConstraint(
            "status IN ('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED')",
            name="ck_access_requests_status",
        ),
        sa.CheckConstraint(
            "scope_type IN ('GLOBAL', 'ORGANISATION', 'PROJECT', 'STAGE')",
            name="ck_access_requests_scope_type",
        ),
    )

    # Indexes for common queries
    op.create_index("ix_access_requests_status", "access_requests", ["status"])
    op.create_index(
        "ix_access_requests_organisation_id", "access_requests", ["organisation_id"]
    )
    op.create_index(
        "ix_access_requests_target_user_id", "access_requests", ["target_user_id"]
    )


def downgrade() -> None:
    # Drop access_requests
    op.drop_index("ix_access_requests_target_user_id", table_name="access_requests")
    op.drop_index("ix_access_requests_organisation_id", table_name="access_requests")
    op.drop_index("ix_access_requests_status", table_name="access_requests")
    op.drop_table("access_requests")

    # Restore user_roles to original state
    op.drop_index("uq_user_roles_scoped", table_name="user_roles")
    op.drop_index("uq_user_roles_global", table_name="user_roles")
    op.drop_constraint("ck_user_roles_scope_type", "user_roles", type_="check")
    op.create_unique_constraint(
        "user_roles_user_id_role_id_scope_type_scope_id_key",
        "user_roles",
        ["user_id", "role_id", "scope_type", "scope_id"],
    )
    op.alter_column("user_roles", "scope_type", nullable=True, server_default=None)

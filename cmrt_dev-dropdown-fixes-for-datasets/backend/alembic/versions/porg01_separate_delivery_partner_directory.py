"""separate delivery partner directory from registered organizations

Revision ID: porg01_partner_directory
Revises: all current migration heads
Create Date: 2026-10-21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "porg01_partner_directory"
down_revision = (
    "z4c5d6e7f8a9",
    "b2c3d4e5",
    "cr01_concrete_register",
    "er04_merge_heads",
    "b1c2d3e4f5a6",
    "z2a3b4c5d6e7",
    "bb1cc2dd3ee4",
    "e5f6a7b8c9d0",
    "a1b2c3d4",
    "n1o2p3q4r5s6",
    "a9b8c7d6e5f4",
    "dr01_drop_concrete_mix_tables",
    "b6b7lc000001",
    "v1w2x3y4z5a6",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "organization",
        sa.Column("is_registration_org", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.create_table(
        "partner_organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("normalized_name", sa.String(255), nullable=False),
        sa.Column("partner_type", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("partner_type IN ('DESIGNERS', 'CONTRACTORS')", name="ck_partner_organizations_type"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("partner_type", "normalized_name", name="uq_partner_organizations_type_normalized_name"),
    )
    op.create_index(
        "ix_partner_organizations_type_active_name",
        "partner_organizations",
        ["partner_type", "is_active", "name"],
    )

    op.create_table(
        "partner_organization_suggestions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("normalized_name", sa.String(255), nullable=False),
        sa.Column("partner_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(12), server_default="pending", nullable=False),
        sa.Column("submitted_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("partner_organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), server_default=sa.func.now(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=False), nullable=True),
        sa.CheckConstraint("partner_type IN ('DESIGNERS', 'CONTRACTORS')", name="ck_partner_org_suggestions_type"),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="ck_partner_org_suggestions_status"),
        sa.ForeignKeyConstraint(["partner_organization_id"], ["partner_organizations.id"]),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["submitted_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_partner_org_suggestion_pending_name",
        "partner_organization_suggestions",
        ["partner_type", "normalized_name"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "ix_partner_org_suggestions_status_created",
        "partner_organization_suggestions",
        ["status", "created_at"],
    )

    op.create_table(
        "project_partner_organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("partner_organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("custom_partner_name", sa.String(255), nullable=True),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=False), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "(partner_organization_id IS NOT NULL AND custom_partner_name IS NULL) OR "
            "(partner_organization_id IS NULL AND custom_partner_name IS NOT NULL)",
            name="ck_project_partner_organizations_exactly_one_source",
        ),
        sa.CheckConstraint("role IN ('DESIGNER', 'DELIVERY')", name="ck_project_partner_organizations_role"),
        sa.ForeignKeyConstraint(["partner_organization_id"], ["partner_organizations.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_partner_organizations_project", "project_partner_organizations", ["project_id"])
    op.create_index("ix_project_partner_organizations_partner", "project_partner_organizations", ["partner_organization_id"])

    # Hide rows that only exist because a partner name was auto-created. Keep
    # organizations that also have registered users available for registration.
    op.execute(sa.text("""
        UPDATE organization org
        SET is_registration_org = false
        WHERE EXISTS (
            SELECT 1 FROM project_organizations po
            WHERE po.organization_id = org.id AND po.role IN ('DESIGNER', 'DELIVERY')
        )
          AND NOT EXISTS (
            SELECT 1 FROM users u WHERE u.organization_id = org.id
        )
    """))

    # Preserve the delivery partner names and project roles. Registered
    # organization rows remain untouched and are not referenced by the new tables.
    op.execute(sa.text("""
        WITH legacy AS (
            SELECT DISTINCT
                CASE WHEN po.role = 'DESIGNER' THEN 'DESIGNERS' ELSE 'CONTRACTORS' END AS partner_type,
                btrim(o.name) AS name,
                upper(regexp_replace(btrim(o.name), '[[:space:]]+', ' ', 'g')) AS normalized_name
            FROM project_organizations po
            JOIN organization o ON o.id = po.organization_id
            WHERE po.role IN ('DESIGNER', 'DELIVERY')
              AND btrim(o.name) <> ''
        )
        INSERT INTO partner_organizations (name, normalized_name, partner_type)
        SELECT DISTINCT ON (partner_type, normalized_name)
            name, normalized_name, partner_type
        FROM legacy
        ORDER BY partner_type, normalized_name, name
    """))
    op.execute(sa.text("""
        INSERT INTO project_partner_organizations (
            project_id, partner_organization_id, role
        )
        SELECT po.project_id, partner.id, po.role
        FROM project_organizations po
        JOIN organization o ON o.id = po.organization_id
        JOIN partner_organizations partner
          ON partner.partner_type = CASE WHEN po.role = 'DESIGNER' THEN 'DESIGNERS' ELSE 'CONTRACTORS' END
         AND partner.normalized_name = upper(regexp_replace(btrim(o.name), '[[:space:]]+', ' ', 'g'))
        WHERE po.role IN ('DESIGNER', 'DELIVERY')
          AND btrim(o.name) <> ''
    """))
    op.execute("DELETE FROM project_organizations WHERE role IN ('DESIGNER', 'DELIVERY')")


def downgrade() -> None:
    # The new partner entities are intentionally independent from registered
    # organizations, so mapping them back would recreate the coupling this
    # migration removes and could attach the wrong registered account.
    raise RuntimeError("Partner directory migration is intentionally irreversible; restore from backup to roll back.")

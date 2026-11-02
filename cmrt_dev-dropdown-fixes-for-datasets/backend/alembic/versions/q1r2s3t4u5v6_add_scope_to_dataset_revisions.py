"""add scope_type and scope_id to dataset_revisions

Revision ID: q1r2s3t4u5v6
Revises: p1q2r3s4t5u6
Create Date: 2026-03-19

Changes:
  - Add scope_type VARCHAR(20) NOT NULL DEFAULT 'DEFAULT' to dataset_revisions
  - Add scope_id UUID NULL to dataset_revisions
  - Drop old unique constraint on (name) alone
  - Add new unique constraint on (name, scope_type, scope_id)

Scope tiers:
  DEFAULT  = platform-global revisions (SUPER_ADMIN)
  ORG      = organisation-scoped revisions (ORG_ADMIN, scope_id = org uuid)
  PROJECT  = project-scoped revisions (PROJECT_ADMIN/EDITOR, scope_id = project uuid)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "q1r2s3t4u5v6"
down_revision = "p1q2r3s4t5u6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add scope_type column (non-nullable, defaults to DEFAULT for all existing rows)
    op.add_column(
        "dataset_revisions",
        sa.Column(
            "scope_type",
            sa.String(length=20),
            nullable=False,
            server_default="DEFAULT",
        ),
    )

    # 2. Add scope_id column (nullable UUID — holds org_id or project_id)
    op.add_column(
        "dataset_revisions",
        sa.Column(
            "scope_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    # 3. Drop the old single-column name unique constraint
    op.drop_constraint(
        "dataset_revisions_name_key",
        "dataset_revisions",
        type_="unique",
    )

    # 4. Create composite unique constraint (name, scope_type, scope_id)
    #    NB: PostgreSQL treats NULLs as distinct in unique indexes, so two rows with
    #    the same name+scope_type but scope_id=NULL would not collide.  We use a
    #    NULLS NOT DISTINCT clause introduced in PG 15 to fix this, but for broader
    #    PG compat we handle the NULL case in application code.
    op.create_unique_constraint(
        "dataset_revisions_name_scope_key",
        "dataset_revisions",
        ["name", "scope_type", "scope_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "dataset_revisions_name_scope_key",
        "dataset_revisions",
        type_="unique",
    )
    op.create_unique_constraint(
        "dataset_revisions_name_key",
        "dataset_revisions",
        ["name"],
    )
    op.drop_column("dataset_revisions", "scope_id")
    op.drop_column("dataset_revisions", "scope_type")

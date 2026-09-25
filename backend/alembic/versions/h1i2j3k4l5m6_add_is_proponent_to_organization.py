"""h1i2j3k4l5m6_add_is_proponent_to_organization.py

Revision ID: h1i2j3k4l5m6
Revises: g1h2i3j4k5l6
Create Date: 2026-03-11

Changes
-------
1.  organization.is_proponent (BOOLEAN NOT NULL DEFAULT TRUE)
    Distinguishes proponent (lead) organisations from non-proponent (supporting)
    organisations.

    Proponent org registration flow:
      - Founding user submits a pending ORG_ADMIN access request (SUPER_ADMIN approves).

    Non-proponent org registration flow:
      - Founding user is registered as a basic org member with no admin request.
      - No SUPER_ADMIN approval required.

    Existing rows inherit is_proponent = TRUE (safe default – preserves the
    previous behaviour for all already-registered organisations).
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "h1i2j3k4l5m6"
down_revision = "g1h2i3j4k5l6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "organization",
        sa.Column(
            "is_proponent",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("organization", "is_proponent")

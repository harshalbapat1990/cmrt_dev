"""add_password_hash_to_users

Revision ID: j1k2l3m4n5o6
Revises: i1j2k3l4m5n6
Create Date: 2026-03-14

Changes
-------
1. Add nullable ``password_hash`` column to the ``users`` table.
   Existing rows keep NULL (they were seeded or created without passwords).
   OIDC users also keep NULL.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'j1k2l3m4n5o6'
down_revision = 'i1j2k3l4m5n6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('password_hash', sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('users', 'password_hash')

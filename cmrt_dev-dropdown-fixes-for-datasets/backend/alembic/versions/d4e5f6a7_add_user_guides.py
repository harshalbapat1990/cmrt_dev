"""Add user_guides table for versioned PDF storage

Revision ID: d4e5f6a7
Revises: c3d4e5f6
Create Date: 2026-05-25

Creates the user_guides table that stores versioned PDF uploads for the
User Guide feature.  The interim storage backend keeps PDF bytes in the
file_data BYTEA column; storage_key is reserved for Azure Blob Storage paths
once that service is provisioned.  Switching backends requires no schema
change — only services/storage_service.py needs updating.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_guides",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column(
            "storage_backend",
            sa.String(length=32),
            nullable=False,
            server_default="db",
        ),
        # Interim: raw PDF bytes (NULL when using Azure Blob)
        sa.Column("file_data", sa.LargeBinary(), nullable=True),
        # Future: Azure Blob Storage path (NULL until blob is connected)
        sa.Column("storage_key", sa.Text(), nullable=True),
        sa.Column(
            "uploaded_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "uploaded_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.create_index("ix_user_guides_is_active", "user_guides", ["is_active"])
    op.create_index("ix_user_guides_version", "user_guides", ["version"])


def downgrade() -> None:
    op.drop_index("ix_user_guides_version", table_name="user_guides")
    op.drop_index("ix_user_guides_is_active", table_name="user_guides")
    op.drop_table("user_guides")

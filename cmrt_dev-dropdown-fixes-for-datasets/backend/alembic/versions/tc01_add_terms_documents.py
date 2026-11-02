"""Add terms_documents table for versioned Terms & Conditions PDFs

Revision ID: tc01_add_terms_documents
Revises: fix01_densities_rec_key
Create Date: 2026-09-08

Creates the terms_documents table, mirroring the user_guides pattern but
scoped by document_type so the Personal Information Collection Statement
and the CMRT Terms of Use are versioned and activated independently.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "tc01_add_terms_documents"
down_revision: Union[str, Sequence[str], None] = "fix01_densities_rec_key"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# create_type=False: creation/drop is handled explicitly below — otherwise
# op.create_table's own enum-column event fires a second, unchecked CREATE TYPE.
_TERMS_DOCUMENT_TYPE_ENUM = postgresql.ENUM(
    "PICS", "TERMS_OF_USE", name="terms_document_type", create_type=False
)


def upgrade() -> None:
    _TERMS_DOCUMENT_TYPE_ENUM.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "terms_documents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("document_type", _TERMS_DOCUMENT_TYPE_ENUM, nullable=False),
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
    op.create_index(
        "ix_terms_documents_type_active",
        "terms_documents",
        ["document_type", "is_active"],
    )
    op.create_index(
        "ix_terms_documents_type_version",
        "terms_documents",
        ["document_type", "version"],
    )


def downgrade() -> None:
    op.drop_index("ix_terms_documents_type_version", table_name="terms_documents")
    op.drop_index("ix_terms_documents_type_active", table_name="terms_documents")
    op.drop_table("terms_documents")
    _TERMS_DOCUMENT_TYPE_ENUM.drop(op.get_bind(), checkfirst=True)

"""Add PICS/Terms-of-Use acceptance tracking to users

Revision ID: pics01_add_acceptance
Revises: tc01_add_terms_documents
Create Date: 2026-09-09

Adds boolean/timestamp/version columns so each user's acceptance of the
Personal Information Collection Statement and CMRT Terms of Use is recorded
permanently and tied to the specific document version they accepted, so a
future document version bump can require re-acceptance.

NOTE: verify with `alembic heads` before applying — if this repo has more
than one head, update down_revision (or add a merge migration) accordingly.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "pics01_add_acceptance"
down_revision: Union[str, Sequence[str], None] = "tc01_add_terms_documents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("pics_accepted", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("users", sa.Column("pics_accepted_at", sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column("users", sa.Column("pics_version", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("terms_accepted", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("users", sa.Column("terms_accepted_at", sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column("users", sa.Column("terms_version", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "terms_version")
    op.drop_column("users", "terms_accepted_at")
    op.drop_column("users", "terms_accepted")
    op.drop_column("users", "pics_version")
    op.drop_column("users", "pics_accepted_at")
    op.drop_column("users", "pics_accepted")

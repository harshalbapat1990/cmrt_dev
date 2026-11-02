"""Add direct_substitution_factors (BAU Direct Substitutions dataset)

Revision ID: ds01_direct_substitution_facts (must be <= 32 chars for alembic_version.version_num)
Revises: rcf01_add_dataset_revision_id
Create Date: 2026-05-18

"""
import json
from pathlib import Path
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision: str = "ds01_direct_substitution_facts"
down_revision: Union[str, Sequence[str], None] = "rcf01_add_dataset_revision_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "direct_substitution_factors",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("jurisdiction_id", sa.UUID(), nullable=False),
        sa.Column("user_emissions_source", sa.Text(), nullable=False),
        sa.Column("user_unit", sa.String(length=64), nullable=False),
        sa.Column("bau_equivalent_emission_source", sa.Text(), nullable=False),
        sa.Column("bau_equivalent_unit", sa.String(length=64), nullable=False),
        sa.Column("bau_quantity_per_user_unit", sa.Numeric(24, 12), nullable=False),
        sa.Column("display_order", sa.Integer(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(["jurisdiction_id"], ["jurisdictions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_direct_substitution_factors_jurisdiction_id",
        "direct_substitution_factors",
        ["jurisdiction_id"],
    )
    op.create_index(
        "ix_direct_substitution_factors_jur_order",
        "direct_substitution_factors",
        ["jurisdiction_id", "display_order"],
    )

    seed_path = Path(__file__).parent / "direct_subs_seed.json"
    rows = json.loads(seed_path.read_text(encoding="utf-8"))
    conn = op.get_bind()
    ins = text(
        """
        INSERT INTO direct_substitution_factors (
          jurisdiction_id, user_emissions_source, user_unit,
          bau_equivalent_emission_source, bau_equivalent_unit,
          bau_quantity_per_user_unit, display_order
        )
        SELECT j.id, :user_src, :user_unit, :bau_src, :bau_unit, :qty, :ord
        FROM jurisdictions j WHERE j.name = :jname LIMIT 1
        """
    )
    for row in rows:
        conn.execute(
            ins,
            {
                "user_src": row["user_emissions_source"],
                "user_unit": row["user_unit"],
                "bau_src": row["bau_equivalent_emission_source"],
                "bau_unit": row["bau_equivalent_unit"],
                "qty": row["bau_quantity_per_user_unit"],
                "ord": row["display_order"],
                "jname": row["jurisdiction_name"],
            },
        )


def downgrade() -> None:
    op.drop_index("ix_direct_substitution_factors_jur_order", table_name="direct_substitution_factors")
    op.drop_index("ix_direct_substitution_factors_jurisdiction_id", table_name="direct_substitution_factors")
    op.drop_table("direct_substitution_factors")

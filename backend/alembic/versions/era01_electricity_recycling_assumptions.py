"""Add electricity_recycling_assumptions (BAU Electricity and Recycling Assumptions)

Revision ID: era01_electricity_recycling
Revises: b2c3d4e5
Create Date: 2026-05-23

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID

revision: str = "era01_electricity_recycling"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_DATASET_REVISION_ID = "d1e03bea-0918-4788-9922-8c5268abadee"

_SEED_ROWS = [
    # Australia
    ("Australia", "onsite_renewable_construction", "On-site renewable energy use (Construction)", "0", False, 10),
    ("Australia", "offsite_renewable_construction", "Off-site renewable energy use (Construction)", "0", False, 20),
    ("Australia", "grid_electricity_construction", "Grid Electricity (Construction)", "1", True, 30),
    ("Australia", "onsite_renewable_operation", "On-site renewable energy use (Operation)", "0", False, 40),
    ("Australia", "offsite_renewable_operation", "Off-site renewable energy use (Operation)", "0", False, 50),
    ("Australia", "grid_electricity_operation", "Grid Electricity (Operation)", "1", True, 60),
    (
        "Australia",
        "inert_waste_concrete_plastics_glass_rubble_recycling",
        "Inert waste - Concrete/ plastics / glass / rubble (Recycling)",
        "0.9",
        False,
        70,
    ),
    ("Australia", "inert_waste_metals_recycling", "Inert waste - Metals (Recycling)", "0.9", False, 80),
    ("Australia", "paper_cardboard_recycling", "Paper and cardboard (Recycling)", "0.5", False, 90),
    ("Australia", "garden_green_recycling", "Garden and green (Recycling)", "0.51", False, 100),
    ("Australia", "wood_recycling", "Wood (Recycling)", "0.45", False, 110),
    (
        "Australia",
        "mixed_construction_demolition_waste_recycling",
        "Mixed construction and demolition waste (Recycling)",
        "0.83",
        False,
        120,
    ),
    # New Zealand
    ("New Zealand", "onsite_renewable_construction", "On-site renewable energy use (Construction)", "0", False, 10),
    ("New Zealand", "offsite_renewable_construction", "Off-site renewable energy use (Construction)", "0", False, 20),
    ("New Zealand", "grid_electricity_construction", "Grid Electricity (Construction)", "1", True, 30),
    ("New Zealand", "onsite_renewable_operation", "On-site renewable energy use (Operation)", "0", False, 40),
    ("New Zealand", "offsite_renewable_operation", "Off-site renewable energy use (Operation)", "0", False, 50),
    ("New Zealand", "grid_electricity_operation", "Grid Electricity (Operation)", "1", True, 60),
    (
        "New Zealand",
        "inert_waste_concrete_plastics_glass_rubble_recycling",
        "Inert waste - Concrete/ plastics / glass / rubble (Recycling)",
        "0.9",
        False,
        70,
    ),
    ("New Zealand", "inert_waste_metals_recycling", "Inert waste - Metals (Recycling)", "0.95", False, 80),
    ("New Zealand", "paper_cardboard_recycling", "Paper and cardboard (Recycling)", "0", False, 90),
    ("New Zealand", "garden_green_recycling", "Garden and green (Recycling)", "0", False, 100),
    ("New Zealand", "wood_recycling", "Wood (Recycling)", "0.25", False, 110),
    (
        "New Zealand",
        "mixed_construction_demolition_waste_recycling",
        "Mixed construction and demolition waste (Recycling)",
        "0",
        False,
        120,
    ),
]


def _insert_seed_rows(conn, revision_id: str | None) -> None:
    ins = text(
        """
        INSERT INTO electricity_recycling_assumptions (
          dataset_revision_id,
          jurisdiction_id,
          metric_code,
          metric_label,
          default_bau_pct,
          is_calculated,
          display_order,
          is_active
        )
        SELECT
          :revision_id,
          j.id,
          :metric_code,
          :metric_label,
          :default_bau_pct,
          :is_calculated,
          :display_order,
          TRUE
        FROM jurisdictions j
        WHERE j.name = :jurisdiction_name
        LIMIT 1
        """
    )
    for jname, code, label, pct, is_calc, order in _SEED_ROWS:
        conn.execute(
            ins,
            {
                "revision_id": revision_id,
                "jurisdiction_name": jname,
                "metric_code": code,
                "metric_label": label,
                "default_bau_pct": pct,
                "is_calculated": is_calc,
                "display_order": order,
            },
        )


def upgrade() -> None:
    op.create_table(
        "electricity_recycling_assumptions",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "dataset_revision_id",
            UUID(as_uuid=True),
            sa.ForeignKey("dataset_revisions.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "jurisdiction_id",
            UUID(as_uuid=True),
            sa.ForeignKey("jurisdictions.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column("metric_code", sa.String(length=64), nullable=False),
        sa.Column("metric_label", sa.Text(), nullable=False),
        sa.Column(
            "default_bau_pct",
            sa.Numeric(8, 6),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "is_calculated",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
        sa.Column(
            "display_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("TRUE"),
        ),
        sa.Column(
            "created_on",
            sa.TIMESTAMP(timezone=False),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column("updated_on", sa.TIMESTAMP(timezone=False), nullable=True),
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_electricity_recycling_assumptions_global "
        "ON electricity_recycling_assumptions (jurisdiction_id, metric_code) "
        "WHERE dataset_revision_id IS NULL AND is_active = TRUE"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_electricity_recycling_assumptions_revision "
        "ON electricity_recycling_assumptions (dataset_revision_id, jurisdiction_id, metric_code) "
        "WHERE dataset_revision_id IS NOT NULL AND is_active = TRUE"
    )
    op.create_index(
        "ix_electricity_recycling_assumptions_jur_order",
        "electricity_recycling_assumptions",
        ["dataset_revision_id", "jurisdiction_id", "display_order"],
    )

    conn = op.get_bind()
    _insert_seed_rows(conn, None)

    conn.execute(
        text(
            """
            INSERT INTO electricity_recycling_assumptions (
              dataset_revision_id,
              jurisdiction_id,
              metric_code,
              metric_label,
              default_bau_pct,
              is_calculated,
              display_order,
              is_active
            )
            SELECT
              :revision_id,
              e.jurisdiction_id,
              e.metric_code,
              e.metric_label,
              e.default_bau_pct,
              e.is_calculated,
              e.display_order,
              TRUE
            FROM electricity_recycling_assumptions e
            WHERE e.dataset_revision_id IS NULL
              AND EXISTS (
                SELECT 1 FROM dataset_revisions dr WHERE dr.id = :revision_id
              )
            """
        ),
        {"revision_id": DEFAULT_DATASET_REVISION_ID},
    )


def downgrade() -> None:
    op.drop_index(
        "ix_electricity_recycling_assumptions_jur_order",
        table_name="electricity_recycling_assumptions",
    )
    op.execute("DROP INDEX IF EXISTS uq_electricity_recycling_assumptions_revision")
    op.execute("DROP INDEX IF EXISTS uq_electricity_recycling_assumptions_global")
    op.drop_table("electricity_recycling_assumptions")

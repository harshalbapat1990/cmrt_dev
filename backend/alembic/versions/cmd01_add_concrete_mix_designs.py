"""add concrete_mix_assumptions and concrete_mix_designs (BAU)

Revision ID: cmd01_concrete_mix_designs
Revises: pc01_backfill_pc_jur
Create Date: 2026-05-07 00:00:00.000000

Creates the two tables that back the new "Default concrete mix designs"
dataset under the "Business-as-usual Assumptions" group on the Datasets
screen and seeds the default global rows from the platform-default
concrete mix design table.

Only the user-editable rows are persisted; the calculated rows
(General purpose cement, Fly ash, GGBF slag) are derived in the UI from
the assumptions plus the "Total cementitious content" row.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "cmd01_concrete_mix_designs"
down_revision: Union[str, Sequence[str], None] = "pc01_backfill_pc_jur"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Default global mix content (kg/m3) per strength grade, matching the
# Default concrete mix designs spec sheet.
_SEED_ROWS = [
    {
        "component_code": "total_cementitious_content",
        "component_label": "Total cementitious content",
        "display_order": 10,
        "strength_20_kg_m3": 280,
        "strength_25_kg_m3": 310,
        "strength_32_kg_m3": 360,
        "strength_40_kg_m3": 440,
        "strength_50_kg_m3": 550,
        "strength_65_kg_m3": 550,
        "strength_80_kg_m3": 610,
        "strength_100_kg_m3": 660,
    },
    {
        "component_code": "silica_fume",
        "component_label": "Silica Fume",
        "display_order": 50,
        "strength_20_kg_m3": 0,
        "strength_25_kg_m3": 0,
        "strength_32_kg_m3": 0,
        "strength_40_kg_m3": 0,
        "strength_50_kg_m3": 0,
        "strength_65_kg_m3": 0,
        "strength_80_kg_m3": 0,
        "strength_100_kg_m3": 0,
    },
    {
        "component_code": "fine_aggregates",
        "component_label": "Fine Aggregates",
        "display_order": 60,
        "strength_20_kg_m3": 918,
        "strength_25_kg_m3": 881,
        "strength_32_kg_m3": 812,
        "strength_40_kg_m3": 707,
        "strength_50_kg_m3": 556,
        "strength_65_kg_m3": 561,
        "strength_80_kg_m3": 499,
        "strength_100_kg_m3": 465,
    },
    {
        "component_code": "coarse_aggregates",
        "component_label": "Coarse Aggregates",
        "display_order": 70,
        "strength_20_kg_m3": 990,
        "strength_25_kg_m3": 1000,
        "strength_32_kg_m3": 1010,
        "strength_40_kg_m3": 1030,
        "strength_50_kg_m3": 1070,
        "strength_65_kg_m3": 1100,
        "strength_80_kg_m3": 1100,
        "strength_100_kg_m3": 1100,
    },
    {
        "component_code": "recycled_aggregates",
        "component_label": "Recycled Aggregates",
        "display_order": 80,
        "strength_20_kg_m3": 0,
        "strength_25_kg_m3": 0,
        "strength_32_kg_m3": 0,
        "strength_40_kg_m3": 0,
        "strength_50_kg_m3": 0,
        "strength_65_kg_m3": 0,
        "strength_80_kg_m3": 0,
        "strength_100_kg_m3": 0,
    },
    {
        "component_code": "manufactured_sand",
        "component_label": "Manufactured sand",
        "display_order": 90,
        "strength_20_kg_m3": 0,
        "strength_25_kg_m3": 0,
        "strength_32_kg_m3": 0,
        "strength_40_kg_m3": 0,
        "strength_50_kg_m3": 0,
        "strength_65_kg_m3": 0,
        "strength_80_kg_m3": 0,
        "strength_100_kg_m3": 0,
    },
    {
        "component_code": "mains_water",
        "component_label": "Mains Water",
        "display_order": 100,
        "strength_20_kg_m3": 210,
        "strength_25_kg_m3": 207,
        "strength_32_kg_m3": 216,
        "strength_40_kg_m3": 220,
        "strength_50_kg_m3": 220,
        "strength_65_kg_m3": 183,
        "strength_80_kg_m3": 183,
        "strength_100_kg_m3": 165,
    },
    {
        "component_code": "onsite_recycled_water",
        "component_label": "Onsite Recycled / Captured Water",
        "display_order": 110,
        "strength_20_kg_m3": 0,
        "strength_25_kg_m3": 0,
        "strength_32_kg_m3": 0,
        "strength_40_kg_m3": 0,
        "strength_50_kg_m3": 0,
        "strength_65_kg_m3": 0,
        "strength_80_kg_m3": 0,
        "strength_100_kg_m3": 0,
    },
    {
        "component_code": "admixture",
        "component_label": "Admixture",
        "display_order": 120,
        "strength_20_kg_m3": 2,
        "strength_25_kg_m3": 2,
        "strength_32_kg_m3": 2,
        "strength_40_kg_m3": 3,
        "strength_50_kg_m3": 4,
        "strength_65_kg_m3": 6,
        "strength_80_kg_m3": 8,
        "strength_100_kg_m3": 10,
    },
]


def upgrade() -> None:
    # ── concrete_mix_assumptions ────────────────────────────────────────────
    assumptions_table = op.create_table(
        "concrete_mix_assumptions",
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
            "bau_scm_content_pct",
            sa.Numeric(6, 4),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "default_max_fly_ash_pct",
            sa.Numeric(6, 4),
            nullable=False,
            server_default=sa.text("0.30"),
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
        "CREATE UNIQUE INDEX uq_concrete_mix_assumptions_global "
        "ON concrete_mix_assumptions (dataset_revision_id) "
        "WHERE dataset_revision_id IS NULL AND is_active = TRUE"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_concrete_mix_assumptions_revision "
        "ON concrete_mix_assumptions (dataset_revision_id) "
        "WHERE dataset_revision_id IS NOT NULL AND is_active = TRUE"
    )

    # Seed the global default assumptions row.
    op.bulk_insert(
        assumptions_table,
        [
            {
                "dataset_revision_id": None,
                "bau_scm_content_pct": 0,
                "default_max_fly_ash_pct": 0.30,
                "is_active": True,
            }
        ],
    )

    # ── concrete_mix_designs ────────────────────────────────────────────────
    designs_table = op.create_table(
        "concrete_mix_designs",
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
        sa.Column("component_code", sa.String(64), nullable=False),
        sa.Column("component_label", sa.String(255), nullable=False),
        sa.Column(
            "display_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("strength_20_kg_m3", sa.Numeric(12, 4), nullable=True),
        sa.Column("strength_25_kg_m3", sa.Numeric(12, 4), nullable=True),
        sa.Column("strength_32_kg_m3", sa.Numeric(12, 4), nullable=True),
        sa.Column("strength_40_kg_m3", sa.Numeric(12, 4), nullable=True),
        sa.Column("strength_50_kg_m3", sa.Numeric(12, 4), nullable=True),
        sa.Column("strength_65_kg_m3", sa.Numeric(12, 4), nullable=True),
        sa.Column("strength_80_kg_m3", sa.Numeric(12, 4), nullable=True),
        sa.Column("strength_100_kg_m3", sa.Numeric(12, 4), nullable=True),
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
        "CREATE UNIQUE INDEX uq_concrete_mix_designs_global_component "
        "ON concrete_mix_designs (component_code) "
        "WHERE dataset_revision_id IS NULL AND is_active = TRUE"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_concrete_mix_designs_revision_component "
        "ON concrete_mix_designs (dataset_revision_id, component_code) "
        "WHERE dataset_revision_id IS NOT NULL AND is_active = TRUE"
    )

    op.bulk_insert(
        designs_table,
        [
            {
                **row,
                "dataset_revision_id": None,
                "is_active": True,
            }
            for row in _SEED_ROWS
        ],
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_concrete_mix_designs_revision_component")
    op.execute("DROP INDEX IF EXISTS uq_concrete_mix_designs_global_component")
    op.drop_table("concrete_mix_designs")

    op.execute("DROP INDEX IF EXISTS uq_concrete_mix_assumptions_revision")
    op.execute("DROP INDEX IF EXISTS uq_concrete_mix_assumptions_global")
    op.drop_table("concrete_mix_assumptions")

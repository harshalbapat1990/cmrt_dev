"""Add EV uptake, VEPM, and freight rail factor tables

Revision ID: bb1cc2dd3ee4
Revises: aa1bb2cc3dd4
Create Date: 2026-03-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "bb1cc2dd3ee4"
down_revision = "aa1bb2cc3dd4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. ev_scenario_types lookup ─────────────────────────────────────────
    op.create_table(
        "ev_scenario_types",
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.PrimaryKeyConstraint("code"),
    )
    op.execute(
        """
        INSERT INTO ev_scenario_types (code, name) VALUES
          ('slower_growth',          'Slower Growth'),
          ('step_change',            'Step Change'),
          ('accelerated_transition', 'Accelerated Transition')
        ON CONFLICT (code) DO NOTHING;
        """
    )

    # ── 2. ev_vehicle_categories lookup ─────────────────────────────────────
    op.create_table(
        "ev_vehicle_categories",
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.PrimaryKeyConstraint("code"),
    )
    op.execute(
        """
        INSERT INTO ev_vehicle_categories (code, name) VALUES
          ('articulated_truck',      'Articulated Truck'),
          ('bus',                    'Bus'),
          ('large_light_commercial', 'Large Light Commercial'),
          ('large_residential',      'Large Residential'),
          ('medium_light_commercial','Medium Light Commercial'),
          ('medium_residential',     'Medium Residential'),
          ('motorcycle',             'Motorcycle'),
          ('rigid_truck',            'Rigid Truck'),
          ('small_light_commercial', 'Small Light Commercial'),
          ('small_residential',      'Small Residential')
        ON CONFLICT (code) DO NOTHING;
        """
    )

    # ── 3. ev_energy_types lookup ────────────────────────────────────────────
    op.create_table(
        "ev_energy_types",
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.PrimaryKeyConstraint("code"),
    )
    op.execute(
        """
        INSERT INTO ev_energy_types (code, name) VALUES
          ('bev',    'BEV'),
          ('fcev',   'FCEV'),
          ('hybrid', 'Hybrid'),
          ('ice',    'ICE'),
          ('phev',   'PHEV')
        ON CONFLICT (code) DO NOTHING;
        """
    )

    # ── 4. ev_uptake_factors ─────────────────────────────────────────────────
    op.create_table(
        "ev_uptake_factors",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("dataset_revision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("jurisdiction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scenario_code", sa.String(50), nullable=False),
        sa.Column("vehicle_category_code", sa.String(50), nullable=False),
        sa.Column("energy_type_code", sa.String(50), nullable=False),
        sa.Column("year", sa.SmallInteger(), nullable=False),
        sa.Column("uptake_pct", sa.Numeric(7, 4), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["dataset_revision_id"], ["dataset_revisions.id"],
            name="fk_ev_uptake_dataset_revision_id", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["jurisdiction_id"], ["jurisdictions.id"],
            name="fk_ev_uptake_jurisdiction_id"
        ),
        sa.ForeignKeyConstraint(
            ["scenario_code"], ["ev_scenario_types.code"],
            name="fk_ev_uptake_scenario_code"
        ),
        sa.ForeignKeyConstraint(
            ["vehicle_category_code"], ["ev_vehicle_categories.code"],
            name="fk_ev_uptake_vehicle_category_code"
        ),
        sa.ForeignKeyConstraint(
            ["energy_type_code"], ["ev_energy_types.code"],
            name="fk_ev_uptake_energy_type_code"
        ),
        sa.UniqueConstraint(
            "dataset_revision_id", "jurisdiction_id", "scenario_code",
            "vehicle_category_code", "energy_type_code", "year",
            name="uq_ev_uptake_factors",
        ),
    )
    op.create_index("ix_ev_uptake_factors_dataset_revision_id", "ev_uptake_factors", ["dataset_revision_id"])

    # ── 5. vepm_factors ──────────────────────────────────────────────────────
    op.create_table(
        "vepm_factors",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("dataset_revision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("year", sa.SmallInteger(), nullable=False),
        sa.Column("speed_kmh", sa.SmallInteger(), nullable=False),
        sa.Column("fleet_average_co2e_g_km", sa.Numeric(10, 4), nullable=True),
        sa.Column("light_vehicle_co2e_g_km", sa.Numeric(10, 4), nullable=True),
        sa.Column("heavy_vehicle_co2e_g_km", sa.Numeric(10, 4), nullable=True),
        sa.Column("bus_co2e_g_km", sa.Numeric(10, 4), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["dataset_revision_id"], ["dataset_revisions.id"],
            name="fk_vepm_dataset_revision_id", ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "dataset_revision_id", "year", "speed_kmh",
            name="uq_vepm_factors",
        ),
    )
    op.create_index("ix_vepm_factors_dataset_revision_id", "vepm_factors", ["dataset_revision_id"])

    # ── 6. freight_rail_factors ───────────────────────────────────────────────
    op.create_table(
        "freight_rail_factors",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("dataset_revision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("train_type", sa.String(100), nullable=False),
        sa.Column("terrain", sa.String(50), nullable=False),
        sa.Column("fuel_consumption_l_per_000_gtk", sa.Numeric(10, 4), nullable=True),
        sa.Column("source_note", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["dataset_revision_id"], ["dataset_revisions.id"],
            name="fk_freight_rail_dataset_revision_id", ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "dataset_revision_id", "train_type", "terrain",
            name="uq_freight_rail_factors",
        ),
    )
    op.create_index("ix_freight_rail_factors_dataset_revision_id", "freight_rail_factors", ["dataset_revision_id"])


def downgrade() -> None:
    op.drop_table("freight_rail_factors")
    op.drop_table("vepm_factors")
    op.drop_table("ev_uptake_factors")
    op.drop_table("ev_energy_types")
    op.drop_table("ev_vehicle_categories")
    op.drop_table("ev_scenario_types")

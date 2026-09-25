"""add_vehicle_tables

Revision ID: 1a2b3c4d5e6f
Revises: g7h8i9j0k1l2
Create Date: 2026-04-02 00:00:00.000000

Adds vehicle_classes (lookup) and four vehicle reference-data tables:
  vehicle_masses, interrupted_vehicles, uninterrupted_vehicles,
  vehicle_energy_conversion_rates
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "1a2b3c4d5e6f"
down_revision = "g7h8i9j0k1l2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. vehicle_classes (lookup) ──────────────────────────────────────────
    op.create_table(
        "vehicle_classes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.UniqueConstraint("name", name="uq_vehicle_classes_name"),
    )

    # ── 2. vehicle_masses ────────────────────────────────────────────────────
    op.create_table(
        "vehicle_masses",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "vehicle_class_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vehicle_classes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reference_gcm_tonnes", sa.Numeric(10, 4), nullable=True),
        sa.Column("max_payload_tonnes", sa.Numeric(10, 4), nullable=False),
        sa.Column("gvm_tonnes", sa.Numeric(10, 4), nullable=False),
        sa.Column("assumed_payload_pct", sa.Numeric(5, 2), nullable=False),
        sa.UniqueConstraint("vehicle_class_id", name="uq_vehicle_masses_vehicle_class_id"),
    )

    # ── 3. interrupted_vehicles ──────────────────────────────────────────────
    op.create_table(
        "interrupted_vehicles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "vehicle_class_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vehicle_classes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("coefficient_a", sa.Numeric(12, 6), nullable=False),
        sa.Column("coefficient_b", sa.Numeric(12, 6), nullable=False),
        sa.UniqueConstraint("vehicle_class_id", name="uq_interrupted_vehicles_vehicle_class_id"),
    )

    # ── 4. uninterrupted_vehicles ────────────────────────────────────────────
    op.create_table(
        "uninterrupted_vehicles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "vehicle_class_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vehicle_classes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "gradient_m_per_km",
            sa.Numeric(10, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("curvature_deg_per_km", sa.Numeric(10, 2), nullable=False),
        sa.Column("base_fuel_l_per_100km", sa.Numeric(10, 4), nullable=False),
        sa.Column("k1", sa.Numeric(10, 4), nullable=False),
        sa.Column("k2", sa.Numeric(10, 4), nullable=False),
        sa.Column("k3", sa.Numeric(10, 4), nullable=False),
        sa.Column("k4", sa.Numeric(10, 4), nullable=False),
        sa.Column("k5", sa.Numeric(10, 4), nullable=False),
        sa.UniqueConstraint(
            "vehicle_class_id",
            "gradient_m_per_km",
            "curvature_deg_per_km",
            name="uq_uninterrupted_vehicles_class_gradient_curvature",
        ),
    )

    # ── 5. vehicle_energy_conversion_rates ───────────────────────────────────
    op.create_table(
        "vehicle_energy_conversion_rates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "vehicle_class_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vehicle_classes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ev_projection_category", sa.String(100), nullable=False),
        sa.Column("primary_ice_fuel", sa.String(200), nullable=False),
        sa.Column("hybrid_fuel_savings_pct", sa.Numeric(6, 4), nullable=False),
        sa.Column("phev_fuel_savings_pct", sa.Numeric(6, 4), nullable=False),
        sa.Column("bev_energy_shift_kwh_per_l", sa.Numeric(10, 4), nullable=False),
        sa.Column("fcev_hydrogen_consumption_kwh_per_l", sa.Numeric(10, 4), nullable=False),
        sa.Column("source_comments", sa.Text(), nullable=True),
        sa.UniqueConstraint(
            "vehicle_class_id",
            name="uq_vehicle_energy_conversion_rates_vehicle_class_id",
        ),
    )


def downgrade() -> None:
    op.drop_table("vehicle_energy_conversion_rates")
    op.drop_table("uninterrupted_vehicles")
    op.drop_table("interrupted_vehicles")
    op.drop_table("vehicle_masses")
    op.drop_table("vehicle_classes")

"""add dataset_revision_id to unit and vehicle reference tables

Revision ID: dt01_add_dataset_revision_id_to_unit_and_vehicle_tables
Revises: mrf02_emit_cols
Create Date: 2026-07-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "dt01_add_rev_id_vehicles"
down_revision = "mrf02_emit_cols"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "unit_conversions",
        sa.Column("dataset_revision_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_unit_conversions_dataset_revision_id",
        "unit_conversions",
        "dataset_revisions",
        ["dataset_revision_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_unit_conversions_dataset_revision_id",
        "unit_conversions",
        ["dataset_revision_id"],
        unique=False,
    )
    op.drop_constraint("unit_conversions_from_unit_id_to_unit_id_key", "unit_conversions", type_="unique")
    op.create_index(
        "uq_unit_conversions_global",
        "unit_conversions",
        ["from_unit_id", "to_unit_id"],
        unique=True,
        postgresql_where=sa.text("dataset_revision_id IS NULL"),
    )
    op.create_index(
        "uq_unit_conversions_revision",
        "unit_conversions",
        ["from_unit_id", "to_unit_id", "dataset_revision_id"],
        unique=True,
        postgresql_where=sa.text("dataset_revision_id IS NOT NULL"),
    )

    op.add_column(
        "interrupted_vehicles",
        sa.Column("dataset_revision_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_interrupted_vehicles_dataset_revision_id",
        "interrupted_vehicles",
        "dataset_revisions",
        ["dataset_revision_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_interrupted_vehicles_dataset_revision_id",
        "interrupted_vehicles",
        ["dataset_revision_id"],
        unique=False,
    )
    op.drop_constraint(
        "uq_interrupted_vehicles_vehicle_class_id",
        "interrupted_vehicles",
        type_="unique",
    )
    op.create_index(
        "uq_interrupted_vehicles_global",
        "interrupted_vehicles",
        ["vehicle_class_id"],
        unique=True,
        postgresql_where=sa.text("dataset_revision_id IS NULL"),
    )
    op.create_index(
        "uq_interrupted_vehicles_revision",
        "interrupted_vehicles",
        ["vehicle_class_id", "dataset_revision_id"],
        unique=True,
        postgresql_where=sa.text("dataset_revision_id IS NOT NULL"),
    )

    op.add_column(
        "uninterrupted_vehicles",
        sa.Column("dataset_revision_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_uninterrupted_vehicles_dataset_revision_id",
        "uninterrupted_vehicles",
        "dataset_revisions",
        ["dataset_revision_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_uninterrupted_vehicles_dataset_revision_id",
        "uninterrupted_vehicles",
        ["dataset_revision_id"],
        unique=False,
    )
    op.drop_constraint(
        "uq_uninterrupted_vehicles_class_gradient_curvature",
        "uninterrupted_vehicles",
        type_="unique",
    )
    op.create_index(
        "uq_uninterrupted_vehicles_global",
        "uninterrupted_vehicles",
        ["vehicle_class_id", "gradient_m_per_km", "curvature_deg_per_km"],
        unique=True,
        postgresql_where=sa.text("dataset_revision_id IS NULL"),
    )
    op.create_index(
        "uq_uninterrupted_vehicles_revision",
        "uninterrupted_vehicles",
        ["vehicle_class_id", "gradient_m_per_km", "curvature_deg_per_km", "dataset_revision_id"],
        unique=True,
        postgresql_where=sa.text("dataset_revision_id IS NOT NULL"),
    )

    op.add_column(
        "vehicle_energy_conversion_rates",
        sa.Column("dataset_revision_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_vehicle_energy_conversion_rates_dataset_revision_id",
        "vehicle_energy_conversion_rates",
        "dataset_revisions",
        ["dataset_revision_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_vehicle_energy_conversion_rates_dataset_revision_id",
        "vehicle_energy_conversion_rates",
        ["dataset_revision_id"],
        unique=False,
    )
    op.drop_constraint(
        "uq_vehicle_energy_conversion_rates_vehicle_class_id",
        "vehicle_energy_conversion_rates",
        type_="unique",
    )
    op.create_index(
        "uq_vehicle_energy_conversion_rates_global",
        "vehicle_energy_conversion_rates",
        ["vehicle_class_id"],
        unique=True,
        postgresql_where=sa.text("dataset_revision_id IS NULL"),
    )
    op.create_index(
        "uq_vehicle_energy_conversion_rates_revision",
        "vehicle_energy_conversion_rates",
        ["vehicle_class_id", "dataset_revision_id"],
        unique=True,
        postgresql_where=sa.text("dataset_revision_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_vehicle_energy_conversion_rates_revision", table_name="vehicle_energy_conversion_rates")
    op.drop_index("uq_vehicle_energy_conversion_rates_global", table_name="vehicle_energy_conversion_rates")
    op.create_unique_constraint(
        "uq_vehicle_energy_conversion_rates_vehicle_class_id",
        "vehicle_energy_conversion_rates",
        ["vehicle_class_id"],
    )
    op.drop_index(
        "ix_vehicle_energy_conversion_rates_dataset_revision_id",
        table_name="vehicle_energy_conversion_rates",
    )
    op.drop_constraint(
        "fk_vehicle_energy_conversion_rates_dataset_revision_id",
        "vehicle_energy_conversion_rates",
        type_="foreignkey",
    )
    op.drop_column("vehicle_energy_conversion_rates", "dataset_revision_id")

    op.drop_index("uq_uninterrupted_vehicles_revision", table_name="uninterrupted_vehicles")
    op.drop_index("uq_uninterrupted_vehicles_global", table_name="uninterrupted_vehicles")
    op.create_unique_constraint(
        "uq_uninterrupted_vehicles_class_gradient_curvature",
        "uninterrupted_vehicles",
        ["vehicle_class_id", "gradient_m_per_km", "curvature_deg_per_km"],
    )
    op.drop_index("ix_uninterrupted_vehicles_dataset_revision_id", table_name="uninterrupted_vehicles")
    op.drop_constraint(
        "fk_uninterrupted_vehicles_dataset_revision_id",
        "uninterrupted_vehicles",
        type_="foreignkey",
    )
    op.drop_column("uninterrupted_vehicles", "dataset_revision_id")

    op.drop_index("uq_interrupted_vehicles_revision", table_name="interrupted_vehicles")
    op.drop_index("uq_interrupted_vehicles_global", table_name="interrupted_vehicles")
    op.create_unique_constraint(
        "uq_interrupted_vehicles_vehicle_class_id",
        "interrupted_vehicles",
        ["vehicle_class_id"],
    )
    op.drop_index("ix_interrupted_vehicles_dataset_revision_id", table_name="interrupted_vehicles")
    op.drop_constraint(
        "fk_interrupted_vehicles_dataset_revision_id",
        "interrupted_vehicles",
        type_="foreignkey",
    )
    op.drop_column("interrupted_vehicles", "dataset_revision_id")

    op.drop_index("uq_unit_conversions_revision", table_name="unit_conversions")
    op.drop_index("uq_unit_conversions_global", table_name="unit_conversions")
    op.create_unique_constraint(
        "unit_conversions_from_unit_id_to_unit_id_key",
        "unit_conversions",
        ["from_unit_id", "to_unit_id"],
    )
    op.drop_index("ix_unit_conversions_dataset_revision_id", table_name="unit_conversions")
    op.drop_constraint(
        "fk_unit_conversions_dataset_revision_id",
        "unit_conversions",
        type_="foreignkey",
    )
    op.drop_column("unit_conversions", "dataset_revision_id")
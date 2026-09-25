"""Add electric decarb factors tables

Revision ID: v1w2x3y4z5a6
Revises: u1v2w3x4y5z6
Create Date: 2026-03-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "v1w2x3y4z5a6"
down_revision = "u1v2w3x4y5z6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. decarb_factor_types lookup (code as PK) ──────────────────────────
    op.create_table(
        "decarb_factor_types",
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("has_region", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.PrimaryKeyConstraint("code"),
    )

    # Seed the 5 factor types immediately
    op.execute(
        """
        INSERT INTO decarb_factor_types (code, name, has_region, unit) VALUES
          ('scope2_location', 'Scope 2 Location-based',              TRUE,  'tCO2e/kWh'),
          ('scope2_market',   'Scope 2 Market-based',                FALSE, 'tCO2e/kWh'),
          ('scope3_location', 'Scope 3 Location-based',              TRUE,  'tCO2e/kWh'),
          ('scope3_market',   'Scope 3 Market-based',                FALSE, 'tCO2e/kWh'),
          ('renewable_pct',   'Renewable Power Percentage Market-based', FALSE, '%')
        ON CONFLICT (code) DO NOTHING;
        """
    )

    # ── 2. grid_regions ─────────────────────────────────────────────────────
    op.create_table(
        "grid_regions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("jurisdiction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["jurisdiction_id"], ["jurisdictions.id"]),
        sa.UniqueConstraint("jurisdiction_id", "name", name="uq_grid_regions_jur_name"),
    )
    op.create_index("ix_grid_regions_jurisdiction_id", "grid_regions", ["jurisdiction_id"])

    # Seed AU grid regions + NZ National
    op.execute(
        """
        INSERT INTO grid_regions (jurisdiction_id, name)
        SELECT j.id, r.name
        FROM (VALUES
          ('Australia', 'New South Wales'),
          ('Australia', 'Australian Capital Territory'),
          ('Australia', 'Queensland'),
          ('Australia', 'South Australia'),
          ('Australia', 'Victoria'),
          ('Australia', 'Tasmania'),
          ('Australia', 'Western Australia'),
          ('Australia', 'Northern Territory'),
          ('New Zealand', 'National')
        ) AS r(jur, name)
        JOIN jurisdictions j ON j.name = r.jur
        ON CONFLICT (jurisdiction_id, name) DO NOTHING;
        """
    )

    # ── 3. electric_decarb_factors ──────────────────────────────────────────
    op.create_table(
        "electric_decarb_factors",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("dataset_revision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("factor_type_code", sa.String(50), nullable=False),
        sa.Column("jurisdiction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("region_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("year", sa.SmallInteger(), nullable=False),
        sa.Column("value", sa.Numeric(10, 6), nullable=True),
        sa.Column("value_qualifier", sa.String(5), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["dataset_revision_id"], ["dataset_revisions.id"],
            name="fk_edf_dataset_revision_id", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["factor_type_code"], ["decarb_factor_types.code"],
            name="fk_edf_factor_type_code"
        ),
        sa.ForeignKeyConstraint(
            ["jurisdiction_id"], ["jurisdictions.id"],
            name="fk_edf_jurisdiction_id"
        ),
        sa.ForeignKeyConstraint(
            ["region_id"], ["grid_regions.id"],
            name="fk_edf_region_id"
        ),
    )
    op.create_index("ix_edf_dataset_revision_id", "electric_decarb_factors", ["dataset_revision_id"])

    # Partial unique indexes
    op.execute(
        """
        CREATE UNIQUE INDEX uq_edf_no_region ON electric_decarb_factors
          (dataset_revision_id, factor_type_code, jurisdiction_id, year)
          WHERE region_id IS NULL;
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_edf_with_region ON electric_decarb_factors
          (dataset_revision_id, factor_type_code, region_id, year)
          WHERE region_id IS NOT NULL;
        """
    )


def downgrade() -> None:
    op.drop_table("electric_decarb_factors")
    op.drop_table("grid_regions")
    op.drop_table("decarb_factor_types")

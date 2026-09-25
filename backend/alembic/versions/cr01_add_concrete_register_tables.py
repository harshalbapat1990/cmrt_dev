"""add_concrete_register_tables

Revision ID: cr01_concrete_register
Revises: 4299170e880a, cp02_fix_period_unique
Create Date: 2026-04-28 00:00:00.000000

Creates two tables for the Concrete Register (grade 3/4) feature:
  - concrete_mix      : one row per mix entry across all three data-entry
                        methods (simplified, mix_design, epd_pcf). The
                        `method` discriminator column controls which columns
                        are relevant.
  - concrete_mix_material : sub-row materials belonging to a Mix Design mix.
                            Cascade-deleted when the parent mix is deleted.

The `emissions_tco2e` column defaults to 0; it will be updated by a
dedicated calculation endpoint (developed separately) once available.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "cr01_concrete_register"
down_revision = ("4299170e880a", "cp02_fix_period_unique")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── concrete_mix ──────────────────────────────────────────────────────────
    op.create_table(
        "concrete_mix",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("project.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Discriminator: 'simplified' | 'mix_design' | 'epd_pcf'
        sa.Column("method", sa.String(20), nullable=False),
        # Simplified + Mix Design columns
        sa.Column("mix_type", sa.String(20), nullable=True),
        sa.Column("strength_mpa", sa.Integer(), nullable=True),
        sa.Column("scm_pct", sa.Numeric(6, 2), nullable=True),
        # Mix Design + EPD/PCF columns
        sa.Column("mix_id_label", sa.String(100), nullable=True),
        # EPD/PCF columns
        sa.Column("gwp_a1a3", sa.Numeric(14, 6), nullable=True),
        # Shared columns
        sa.Column("volume_m3", sa.Numeric(12, 4), nullable=True),
        # Emissions: populated by calc endpoint; 0 until then
        sa.Column(
            "emissions_tco2e",
            sa.Numeric(14, 6),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_on",
            sa.TIMESTAMP(timezone=False),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column("updated_on", sa.TIMESTAMP(timezone=False), nullable=True),
    )
    op.create_index("ix__concrete_mix__project_id", "concrete_mix", ["project_id"])
    op.create_index("ix__concrete_mix__method", "concrete_mix", ["method"])

    # ── concrete_mix_material ─────────────────────────────────────────────────
    op.create_table(
        "concrete_mix_material",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "concrete_mix_id",
            UUID(as_uuid=True),
            sa.ForeignKey("concrete_mix.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("material_name", sa.String(200), nullable=False, server_default=""),
        sa.Column("quantity_kg_m3", sa.Numeric(12, 6), nullable=True),
        sa.Column("carbon_factor", sa.Numeric(12, 6), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_on",
            sa.TIMESTAMP(timezone=False),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column("updated_on", sa.TIMESTAMP(timezone=False), nullable=True),
    )
    op.create_index(
        "ix__concrete_mix_material__concrete_mix_id",
        "concrete_mix_material",
        ["concrete_mix_id"],
    )


def downgrade() -> None:
    op.drop_table("concrete_mix_material")
    op.drop_table("concrete_mix")

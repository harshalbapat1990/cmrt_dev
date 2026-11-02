"""drop_concrete_mix_tables

Revision ID: dr01_drop_concrete_mix_tables
Revises: fb53ab048e95
Create Date: 2025-01-01 00:00:00.000000

Concrete mix and concrete mix material data are now stored in the
activity_data table (same as all other tables), keyed by
ui_table_key = 'concreteRegSimplified' | 'concreteRegDetailed'.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "dr01_drop_concrete_mix_tables"
down_revision = "fb53ab048e95"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop FK-dependent table first
    op.drop_table("concrete_mix_material")
    op.drop_table("concrete_mix")


def downgrade() -> None:
    # Recreate concrete_mix
    op.create_table(
        "concrete_mix",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("method", sa.String(), nullable=False),
        sa.Column("mix_type", sa.String(), nullable=True),
        sa.Column("strength_mpa", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("scm_pct", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("volume_m3", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("gwp_a1a3_kgco2e_m3", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("emissions_tco2e", sa.Numeric(precision=16, scale=6), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Recreate concrete_mix_material
    op.create_table(
        "concrete_mix_material",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("mix_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("material_name", sa.String(), nullable=True),
        sa.Column("quantity_kg_m3", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("carbon_factor", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["mix_id"], ["concrete_mix.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

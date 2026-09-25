"""Replace string category/emissions fields with FK references to emissions_categories.

Changes:
- densities: drop emissions_category (str) + emissions_sub_category (str),
             add emissions_category_id (UUID FK) + emissions_sub_category_id (UUID FK)
- materials: drop category (str), add emissions_category_id (UUID FK)
- default_transport_distances: drop material_or_category (str),
                               add material_id (UUID FK) + emissions_category_id (UUID FK),
                               replace unique constraint
- base_case_assumptions: drop category (str), add emissions_category_id (UUID FK),
                         update unique constraint

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-03-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── densities ─────────────────────────────────────────────────────────────
    op.drop_column("densities", "emissions_category")
    op.drop_column("densities", "emissions_sub_category")
    op.add_column(
        "densities",
        sa.Column(
            "emissions_category_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("emissions_categories.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "densities",
        sa.Column(
            "emissions_sub_category_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("emissions_categories.id"),
            nullable=True,
        ),
    )

    # ── materials ─────────────────────────────────────────────────────────────
    op.drop_column("materials", "category")
    op.add_column(
        "materials",
        sa.Column(
            "emissions_category_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("emissions_categories.id"),
            nullable=True,
        ),
    )

    # ── default_transport_distances ───────────────────────────────────────────
    op.drop_constraint(
        "default_transport_distances_jurisdiction_id_material_key",
        "default_transport_distances",
        type_="unique",
    )
    op.drop_column("default_transport_distances", "material_or_category")
    op.add_column(
        "default_transport_distances",
        sa.Column(
            "material_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("materials.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "default_transport_distances",
        sa.Column(
            "emissions_category_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("emissions_categories.id"),
            nullable=True,
        ),
    )
    op.create_unique_constraint(
        "default_transport_distances_jurisdiction_material_category_key",
        "default_transport_distances",
        ["jurisdiction_id", "material_id", "emissions_category_id"],
    )

    # ── base_case_assumptions ─────────────────────────────────────────────────
    op.drop_constraint(
        "base_case_assumptions_category_name_key",
        "base_case_assumptions",
        type_="unique",
    )
    op.drop_column("base_case_assumptions", "category")
    op.add_column(
        "base_case_assumptions",
        sa.Column(
            "emissions_category_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("emissions_categories.id"),
            nullable=True,         # nullable during migration; enforce NOT NULL at app level
        ),
    )
    op.create_unique_constraint(
        "base_case_assumptions_category_name_key",
        "base_case_assumptions",
        ["emissions_category_id", "name"],
    )


def downgrade() -> None:
    # ── base_case_assumptions ─────────────────────────────────────────────────
    op.drop_constraint("base_case_assumptions_category_name_key", "base_case_assumptions", type_="unique")
    op.drop_column("base_case_assumptions", "emissions_category_id")
    op.add_column("base_case_assumptions", sa.Column("category", sa.String(), nullable=True))
    op.create_unique_constraint(
        "base_case_assumptions_category_name_key", "base_case_assumptions", ["category", "name"]
    )

    # ── default_transport_distances ───────────────────────────────────────────
    op.drop_constraint(
        "default_transport_distances_jurisdiction_material_category_key",
        "default_transport_distances",
        type_="unique",
    )
    op.drop_column("default_transport_distances", "emissions_category_id")
    op.drop_column("default_transport_distances", "material_id")
    op.add_column(
        "default_transport_distances",
        sa.Column("material_or_category", sa.String(), nullable=True),
    )
    op.create_unique_constraint(
        "default_transport_distances_jurisdiction_id_material_key",
        "default_transport_distances",
        ["jurisdiction_id", "material_or_category"],
    )

    # ── materials ─────────────────────────────────────────────────────────────
    op.drop_column("materials", "emissions_category_id")
    op.add_column("materials", sa.Column("category", sa.String(), nullable=True))

    # ── densities ─────────────────────────────────────────────────────────────
    op.drop_column("densities", "emissions_sub_category_id")
    op.drop_column("densities", "emissions_category_id")
    op.add_column("densities", sa.Column("emissions_sub_category", sa.String(), nullable=True))
    op.add_column("densities", sa.Column("emissions_category", sa.String(), nullable=True))

"""Normalise BGM mastertype/typecast as FK lookup tables; drop super_sector

Revision ID: u1v2w3x4y5z6
Revises: t1u2v3w4x5y6
Create Date: 2026-03-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "u1v2w3x4y5z6"
down_revision = "t1u2v3w4x5y6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Create benchmark_mastertypes lookup table ───────────────────────
    op.create_table(
        "benchmark_mastertypes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_benchmark_mastertypes_code"),
        sa.UniqueConstraint("name", name="uq_benchmark_mastertypes_name"),
    )

    # ── 2. Create benchmark_typecasts lookup table ─────────────────────────
    op.create_table(
        "benchmark_typecasts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("mastertype_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["mastertype_id"],
            ["benchmark_mastertypes.id"],
            name="fk_benchmark_typecasts_mastertype_id",
        ),
        sa.UniqueConstraint(
            "name", "mastertype_id", name="uq_benchmark_typecasts_name_mastertype"
        ),
    )

    # ── 3. Add new FK columns to background_grade_metrics ─────────────────
    op.add_column(
        "background_grade_metrics",
        sa.Column("mastertype_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "background_grade_metrics",
        sa.Column("typecast_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_bgm_mastertype_id",
        "background_grade_metrics",
        "benchmark_mastertypes",
        ["mastertype_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_bgm_typecast_id",
        "background_grade_metrics",
        "benchmark_typecasts",
        ["typecast_id"],
        ["id"],
    )

    # ── 4. Drop dependent view, then old string columns + index ──────────
    op.execute("DROP VIEW IF EXISTS v_grade1_asset_level_pivoted")
    op.drop_index("ix_bgm_super_sector_mastertype", table_name="background_grade_metrics")
    op.drop_column("background_grade_metrics", "super_sector")
    op.drop_column("background_grade_metrics", "mastertype")
    op.drop_column("background_grade_metrics", "typecast_name")

    # ── 5. New composite index on FK columns ──────────────────────────────
    op.create_index(
        "ix_bgm_mastertype_typecast",
        "background_grade_metrics",
        ["mastertype_id", "typecast_id"],
    )

    # ── 6. Recreate view using FK joins ───────────────────────────────────
    op.execute("""
        CREATE OR REPLACE VIEW v_grade1_asset_level_pivoted AS
        SELECT
            "Jurisdiction",
            "Mastertype",
            "Typecast",
            "Source",
            MAX("Functional_Unit") AS "Functional_Unit",
            MAX(CASE WHEN lifecycle_module_code IS NULL AND band_code = 'Low'  THEN value END) AS "Material share of capex - Low",
            MAX(CASE WHEN lifecycle_module_code IS NULL AND band_code = 'Mid'  THEN value END) AS "Material share of capex - Mid",
            MAX(CASE WHEN lifecycle_module_code IS NULL AND band_code = 'High' THEN value END) AS "Material share of capex - High",
            MAX(CASE WHEN lifecycle_module_code = 'A1-A3' AND band_code = 'Low'  THEN value END) AS "Product stage (A1-A3) - Low",
            MAX(CASE WHEN lifecycle_module_code = 'A1-A3' AND band_code = 'Mid'  THEN value END) AS "Product stage (A1-A3) - Mid",
            MAX(CASE WHEN lifecycle_module_code = 'A1-A3' AND band_code = 'High' THEN value END) AS "Product stage (A1-A3) - High",
            MAX(CASE WHEN lifecycle_module_code = 'A4' AND band_code = 'Low'  THEN value END) AS "transport (A4) - Low",
            MAX(CASE WHEN lifecycle_module_code = 'A4' AND band_code = 'Mid'  THEN value END) AS "transport (A4) - Mid",
            MAX(CASE WHEN lifecycle_module_code = 'A4' AND band_code = 'High' THEN value END) AS "transport (A4) - High",
            MAX(CASE WHEN lifecycle_module_code = 'A5' AND band_code = 'Low'  THEN value END) AS "Construction (A5) - Low",
            MAX(CASE WHEN lifecycle_module_code = 'A5' AND band_code = 'Mid'  THEN value END) AS "Construction (A5) - Mid",
            MAX(CASE WHEN lifecycle_module_code = 'A5' AND band_code = 'High' THEN value END) AS "Construction (A5) - High"
        FROM (
            SELECT DISTINCT ON (
                bgm.jurisdiction_id,
                bgm.typecast_id,
                bgm.source,
                bgm.lifecycle_module_code,
                bgm.band_code,
                bgm.metric_type_id
            )
                j.name      AS "Jurisdiction",
                bmt.name    AS "Mastertype",
                btc.name    AS "Typecast",
                bgm.source  AS "Source",
                u.code      AS "Functional_Unit",
                bgm.lifecycle_module_code,
                bgm.band_code,
                bgm.value
            FROM background_grade_metrics bgm
            JOIN  jurisdictions        j   ON bgm.jurisdiction_id  = j.id
            LEFT JOIN benchmark_mastertypes bmt ON bgm.mastertype_id = bmt.id
            LEFT JOIN benchmark_typecasts   btc ON bgm.typecast_id   = btc.id
            LEFT JOIN units             u   ON bgm.unit_id          = u.id
            WHERE bgm.is_active = true
              AND bgm.grade_id  = 1
            ORDER BY
                bgm.jurisdiction_id,
                bgm.typecast_id,
                bgm.source,
                bgm.lifecycle_module_code,
                bgm.band_code,
                bgm.metric_type_id,
                bgm.created_at DESC,
                bgm.value DESC,
                bgm.id ASC
        ) normalized
        GROUP BY "Jurisdiction", "Mastertype", "Typecast", "Source"
        ORDER BY "Jurisdiction", "Mastertype", "Typecast", "Source"
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_grade1_asset_level_pivoted")
    op.drop_index("ix_bgm_mastertype_typecast", table_name="background_grade_metrics")
    op.drop_constraint("fk_bgm_typecast_id", "background_grade_metrics", type_="foreignkey")
    op.drop_constraint("fk_bgm_mastertype_id", "background_grade_metrics", type_="foreignkey")
    op.drop_column("background_grade_metrics", "typecast_id")
    op.drop_column("background_grade_metrics", "mastertype_id")

    op.add_column("background_grade_metrics", sa.Column("typecast_name", sa.String(), nullable=True))
    op.add_column("background_grade_metrics", sa.Column("mastertype", sa.String(), nullable=True))
    op.add_column("background_grade_metrics", sa.Column("super_sector", sa.String(), nullable=True))
    op.create_index(
        "ix_bgm_super_sector_mastertype",
        "background_grade_metrics",
        ["super_sector", "mastertype"],
    )

    op.drop_table("benchmark_typecasts")
    op.drop_table("benchmark_mastertypes")

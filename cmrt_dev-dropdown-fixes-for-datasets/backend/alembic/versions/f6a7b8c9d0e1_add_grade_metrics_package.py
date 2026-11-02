"""Add Package F (Dataset Revisions & Factor Sets) + Package G (Unified Grade Metrics)

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-03-07

New tables:
  Package F:
    dataset_revisions – versioned snapshots of the benchmark dataset.
    emissions_factor_sets – named grouping of factors for a given jurisdiction/revision.
    project_dataset_revisions – which dataset revision a project is locked to.
    dataset_revision_changes – per-metric audit trail of value changes within a revision.
    project_dataset_exclusions – project-level exclusion of specific benchmark metrics.

  Package G:
    grade_definitions  – Grade 1 / 2 / 3 / 4 reference rows.
    metric_types       – typed codes for each kind of metric (material_share_capex, etc.)
    value_bands        – Low / Mid / High band labels.
    background_grade_metrics – one row per jurisdiction × grade × metric_type × band.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # ------------------------------------------------------------------ #
    # Package F — Dataset Revisions & Factor Sets
    # ------------------------------------------------------------------ #

    op.create_table(
        "dataset_revisions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("applicable_from", sa.Date(), nullable=True),
        sa.Column("applicable_to", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"],
            name="dataset_revisions_created_by_fkey",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="dataset_revisions_name_key"),
    )

    op.create_table(
        "emissions_factor_sets",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("version", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("jurisdiction_id", sa.UUID(), nullable=True),
        sa.Column("dataset_revision_id", sa.UUID(), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["jurisdiction_id"], ["jurisdictions.id"],
            name="emissions_factor_sets_jurisdiction_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_revision_id"], ["dataset_revisions.id"],
            name="emissions_factor_sets_dataset_revision_id_fkey",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "name", "version", "jurisdiction_id",
            name="emissions_factor_sets_name_version_jurisdiction_key",
        ),
    )
    op.create_index(
        "ix_emissions_factor_sets_dataset_revision_id",
        "emissions_factor_sets",
        ["dataset_revision_id"],
    )

    op.create_table(
        "project_dataset_revisions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("dataset_revision_id", sa.UUID(), nullable=False),
        sa.Column("applied_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("now()")),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"], ["project.project_id"],
            name="project_dataset_revisions_project_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_revision_id"], ["dataset_revisions.id"],
            name="project_dataset_revisions_dataset_revision_id_fkey",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id", "dataset_revision_id",
            name="project_dataset_revisions_project_revision_key",
        ),
    )
    op.create_index(
        "ix_project_dataset_revisions_project_id",
        "project_dataset_revisions",
        ["project_id"],
    )
    op.create_index(
        "ix_project_dataset_revisions_dataset_revision_id",
        "project_dataset_revisions",
        ["dataset_revision_id"],
    )

    # ------------------------------------------------------------------ #
    # Package G — Unified Grade Metrics (reference tables first)
    # ------------------------------------------------------------------ #

    op.create_table(
        "grade_definitions",
        sa.Column("id", sa.SmallInteger(), nullable=False, autoincrement=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "metric_types",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="metric_types_code_key"),
    )

    op.create_table(
        "value_bands",
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("sort_order", sa.SmallInteger(), nullable=True),
        sa.PrimaryKeyConstraint("code"),
    )

    # ------------------------------------------------------------------ #
    # background_grade_metrics depends on all the above + jurisdictions,
    # ghg_scopes, units.
    # ------------------------------------------------------------------ #

    op.create_table(
        "background_grade_metrics",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("factor_set_id", sa.UUID(), nullable=False),
        sa.Column("grade_id", sa.SmallInteger(), nullable=False),
        sa.Column("jurisdiction_id", sa.UUID(), nullable=True),
        sa.Column("super_sector", sa.String(), nullable=True),
        sa.Column("mastertype", sa.String(), nullable=True),
        sa.Column("typecast_name", sa.String(), nullable=True),
        sa.Column("emissions_category", sa.String(), nullable=True),
        sa.Column("emissions_subcategory", sa.String(), nullable=True),
        sa.Column("emissions_source", sa.String(), nullable=True),
        sa.Column("lifecycle_module_code", sa.String(), nullable=True),
        sa.Column("ghg_scope_id", sa.SmallInteger(), nullable=True),
        sa.Column("metric_type_id", sa.UUID(), nullable=False),
        sa.Column("band_code", sa.String(), nullable=True),
        sa.Column("unit_id", sa.UUID(), nullable=True),
        sa.Column("value", sa.Numeric(), nullable=True),
        sa.Column("assumed_quantity_default", sa.Numeric(), nullable=True),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["factor_set_id"], ["emissions_factor_sets.id"],
            name="background_grade_metrics_factor_set_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["grade_id"], ["grade_definitions.id"],
            name="background_grade_metrics_grade_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["jurisdiction_id"], ["jurisdictions.id"],
            name="background_grade_metrics_jurisdiction_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["ghg_scope_id"], ["ghg_scopes.id"],
            name="background_grade_metrics_ghg_scope_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["metric_type_id"], ["metric_types.id"],
            name="background_grade_metrics_metric_type_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["band_code"], ["value_bands.code"],
            name="background_grade_metrics_band_code_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["unit_id"], ["units.id"],
            name="background_grade_metrics_unit_id_fkey",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_bgm_factor_set_grade",
        "background_grade_metrics",
        ["factor_set_id", "grade_id"],
    )
    op.create_index(
        "ix_bgm_jurisdiction_category",
        "background_grade_metrics",
        ["jurisdiction_id", "emissions_category", "emissions_subcategory", "emissions_source"],
    )
    op.create_index(
        "ix_bgm_metric_lifecycle_scope",
        "background_grade_metrics",
        ["metric_type_id", "lifecycle_module_code", "ghg_scope_id"],
    )
    op.create_index(
        "ix_bgm_super_sector_mastertype",
        "background_grade_metrics",
        ["super_sector", "mastertype", "typecast_name"],
    )

    # ------------------------------------------------------------------ #
    # dataset_revision_changes + project_dataset_exclusions
    # depend on background_grade_metrics
    # ------------------------------------------------------------------ #

    op.create_table(
        "dataset_revision_changes",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("dataset_revision_id", sa.UUID(), nullable=False),
        sa.Column("metric_id", sa.UUID(), nullable=False),
        sa.Column("change_type", sa.String(50), nullable=False),
        sa.Column("old_value", sa.Numeric(), nullable=True),
        sa.Column("new_value", sa.Numeric(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("changed_by", sa.UUID(), nullable=True),
        sa.Column("changed_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["dataset_revision_id"], ["dataset_revisions.id"],
            name="dataset_revision_changes_dataset_revision_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["metric_id"], ["background_grade_metrics.id"],
            name="dataset_revision_changes_metric_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["changed_by"], ["users.id"],
            name="dataset_revision_changes_changed_by_fkey",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_dataset_revision_changes_revision_id",
        "dataset_revision_changes",
        ["dataset_revision_id"],
    )
    op.create_index(
        "ix_dataset_revision_changes_revision_metric_at",
        "dataset_revision_changes",
        ["dataset_revision_id", "metric_id", "changed_at"],
    )

    op.create_table(
        "project_dataset_exclusions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("metric_id", sa.UUID(), nullable=False),
        sa.Column("excluded_from_revision", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["project_id"], ["project.project_id"],
            name="project_dataset_exclusions_project_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["metric_id"], ["background_grade_metrics.id"],
            name="project_dataset_exclusions_metric_id_fkey",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "metric_id", name="project_dataset_exclusions_project_metric_key"),
    )
    op.create_index(
        "ix_project_dataset_exclusions_project_id",
        "project_dataset_exclusions",
        ["project_id"],
    )
    op.create_index(
        "ix_project_dataset_exclusions_metric_id",
        "project_dataset_exclusions",
        ["metric_id"],
    )


def downgrade() -> None:
    op.drop_table("project_dataset_exclusions")
    op.drop_table("dataset_revision_changes")
    op.drop_index("ix_bgm_super_sector_mastertype", table_name="background_grade_metrics")
    op.drop_index("ix_bgm_metric_lifecycle_scope", table_name="background_grade_metrics")
    op.drop_index("ix_bgm_jurisdiction_category", table_name="background_grade_metrics")
    op.drop_index("ix_bgm_factor_set_grade", table_name="background_grade_metrics")
    op.drop_table("background_grade_metrics")
    op.drop_table("value_bands")
    op.drop_table("metric_types")
    op.drop_table("grade_definitions")
    op.drop_index("ix_project_dataset_revisions_dataset_revision_id", table_name="project_dataset_revisions")
    op.drop_index("ix_project_dataset_revisions_project_id", table_name="project_dataset_revisions")
    op.drop_table("project_dataset_revisions")
    op.drop_index("ix_emissions_factor_sets_dataset_revision_id", table_name="emissions_factor_sets")
    op.drop_table("emissions_factor_sets")
    op.drop_table("dataset_revisions")

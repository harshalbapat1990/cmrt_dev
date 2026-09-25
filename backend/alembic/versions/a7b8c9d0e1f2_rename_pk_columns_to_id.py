"""Rename all *_id primary key columns to id

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-03-09

Renames the primary key column of every table that previously used a
<tablename>_id convention so that it is simply named `id`.  PostgreSQL
automatically updates any foreign-key constraints that point to a renamed
PK column, so no explicit FK constraint drops/recreates are needed.

Affected tables (PK rename old → new):
  project.project_id                               → project.id
  project_type.project_type_id                     → project_type.id
  project_typecast.project_typecast_id             → project_typecast.id
  project_stage_config.project_stage_config_id     → project_stage_config.id
  project_reporting_submission.project_reporting_submission_id → project_reporting_submission.id
  postcode_reference.postcode_reference_id         → postcode_reference.id
  project_postcode.project_postcode_id             → project_postcode.id
  emission_entry.emission_entry_id                 → emission_entry.id
  emission_entry_summary.emission_entry_summary_id → emission_entry_summary.id
  project_organizations.project_organization_link_id → project_organizations.id
  emissions_category.emissions_category_id         → emissions_category.id
  emissions_sub_category.emissions_sub_category_id → emissions_sub_category.id
  measurement_unit.measurement_unit_id             → measurement_unit.id
  emission_source.emission_source_id               → emission_source.id
  emission_factor.emission_factor_id               → emission_factor.id
  emission_factor_value.emission_factor_value_id   → emission_factor_value.id

NOTE: The view `public.v_emission_factor_values_pivot` selects from the
affected lookup tables.  PostgreSQL will automatically update the view's
internal column references when the underlying columns are renamed, but
the view's *output* column aliases (emission_factor_id, emission_source_id,
etc.) remain unchanged because they are explicit aliases in the SELECT list.
No action is required for the view itself.
"""

from typing import Sequence, Union
from alembic import op


revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Helper: one rename per table
# ---------------------------------------------------------------------------

_RENAMES: list[tuple[str, str, str]] = [
    # (table_name, old_column, new_column)
    ("project",                       "project_id",                       "id"),
    ("project_type",                  "project_type_id",                  "id"),
    ("project_typecast",              "project_typecast_id",              "id"),
    ("project_stage_config",          "project_stage_config_id",          "id"),
    ("project_reporting_submission",  "project_reporting_submission_id",  "id"),
    ("postcode_reference",            "postcode_reference_id",            "id"),
    ("project_postcode",              "project_postcode_id",              "id"),
    ("emission_entry",                "emission_entry_id",                "id"),
    ("emission_entry_summary",        "emission_entry_summary_id",        "id"),
    ("project_organizations",         "project_organization_link_id",     "id"),
    ("emissions_category",            "emissions_category_id",            "id"),
    ("emissions_sub_category",        "emissions_sub_category_id",        "id"),
    ("measurement_unit",              "measurement_unit_id",              "id"),
    ("emission_source",               "emission_source_id",               "id"),
    ("emission_factor",               "emission_factor_id",               "id"),
    ("emission_factor_value",         "emission_factor_value_id",         "id"),
]


def upgrade() -> None:
    for table, old_col, new_col in _RENAMES:
        op.execute(
            f'ALTER TABLE "{table}" RENAME COLUMN "{old_col}" TO "{new_col}"'
        )


def downgrade() -> None:
    # Reverse order to respect FK dependencies (children before parents)
    for table, old_col, new_col in reversed(_RENAMES):
        op.execute(
            f'ALTER TABLE "{table}" RENAME COLUMN "{new_col}" TO "{old_col}"'
        )

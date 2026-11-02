"""add value_key and is_supplementary to emissions_results

Revision ID: bfb7c960968a
Revises: 9c867578aa48
Create Date: 2026-05-26

Adds two columns to emissions_results:
  - value_key  (VARCHAR 50, NOT NULL) — stable unique key per result row per activity.
               For lifecycle-stage rows equals the lifecycle_module_code (e.g. 'A1-A3', 'A4').
               For supplementary rows uses a descriptive key (e.g. 'scope1', 'scope3').
  - is_supplementary (BOOLEAN, NOT NULL, DEFAULT FALSE) — marks intermediate / breakdown
               values that should NOT be included in dashboard aggregations.

Replaces the old UNIQUE(activity_data_id, lifecycle_module_code) constraint (which was
fragile against NULL lifecycle_module_code values) with UNIQUE(activity_data_id, value_key).
"""

from alembic import op
import sqlalchemy as sa


revision = 'bfb7c960968a'
down_revision = '9c867578aa48'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add value_key with a temporary default so NOT NULL can be applied immediately
    op.add_column(
        "emissions_results",
        sa.Column("value_key", sa.String(50), nullable=True),
    )

    # 2. Backfill: set value_key = lifecycle_module_code for all existing rows.
    #    Rows that have a NULL lifecycle_module_code (edge-case legacy rows) fall back to 'total'.
    op.execute(
        """
        UPDATE emissions_results
        SET value_key = COALESCE(lifecycle_module_code, 'total')
        """
    )

    # 3. Enforce NOT NULL now that all rows have a value
    op.alter_column("emissions_results", "value_key", nullable=False)

    # 4. Add is_supplementary column (default FALSE — all existing rows are primary results)
    op.add_column(
        "emissions_results",
        sa.Column(
            "is_supplementary",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
    )

    # 5. Deduplicate: legacy rows with NULL lifecycle_module_code all got value_key='total'.
    #    The old UNIQUE(activity_data_id, lifecycle_module_code) allowed multiple NULLs per
    #    activity (NULLs are never equal in PG unique constraints), so we may have several
    #    'total' rows for the same activity. Keep the most-recently-created one.
    op.execute(
        """
        DELETE FROM emissions_results
        WHERE id IN (
            SELECT id FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY activity_data_id, value_key
                           ORDER BY created_at DESC
                       ) AS rn
                FROM emissions_results
                WHERE value_key = 'total'
            ) _dedup
            WHERE rn > 1
        )
        """
    )

    # 6. Drop the old unique constraint (fragile against NULLs in lifecycle_module_code)
    op.drop_constraint(
        "emissions_results_activity_lifecycle_key",
        "emissions_results",
        type_="unique",
    )

    # 7. Add new unique constraint on (activity_data_id, value_key)
    op.create_unique_constraint(
        "emissions_results_activity_value_key",
        "emissions_results",
        ["activity_data_id", "value_key"],
    )


def downgrade() -> None:
    # Restore old constraint and remove new columns
    op.drop_constraint(
        "emissions_results_activity_value_key",
        "emissions_results",
        type_="unique",
    )

    op.create_unique_constraint(
        "emissions_results_activity_lifecycle_key",
        "emissions_results",
        ["activity_data_id", "lifecycle_module_code"],
    )

    op.drop_column("emissions_results", "is_supplementary")
    op.drop_column("emissions_results", "value_key")

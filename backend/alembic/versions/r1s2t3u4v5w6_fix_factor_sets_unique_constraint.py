"""fix emissions_factor_sets unique constraint to include dataset_revision_id

Revision ID: r1s2t3u4v5w6
Revises: q1r2s3t4u5v6
Create Date: 2026-03-19

Problem:
  The old unique constraint on emissions_factor_sets was (name, version, jurisdiction_id).
  This prevented branching a dataset revision because the copied factor sets would have
  the same (name, version, jurisdiction_id) as the source, triggering a conflict.

Fix:
  Replace the constraint with (name, version, jurisdiction_id, dataset_revision_id) so
  uniqueness is scoped within a single revision. The same factor set structure can now
  exist across multiple revisions (which is the entire point of branching).
"""

from alembic import op

# revision identifiers
revision = "r1s2t3u4v5w6"
down_revision = "q1r2s3t4u5v6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old 3-column constraint
    op.drop_constraint(
        "emissions_factor_sets_name_version_jurisdiction_key",
        "emissions_factor_sets",
        type_="unique",
    )
    # Add new 4-column constraint that scopes uniqueness to within a revision
    op.create_unique_constraint(
        "emissions_factor_sets_name_version_jurisdiction_revision_key",
        "emissions_factor_sets",
        ["name", "version", "jurisdiction_id", "dataset_revision_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "emissions_factor_sets_name_version_jurisdiction_revision_key",
        "emissions_factor_sets",
        type_="unique",
    )
    op.create_unique_constraint(
        "emissions_factor_sets_name_version_jurisdiction_key",
        "emissions_factor_sets",
        ["name", "version", "jurisdiction_id"],
    )

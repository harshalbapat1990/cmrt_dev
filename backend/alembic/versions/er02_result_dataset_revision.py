"""record the dataset revision used for each emissions result

Revision ID: er02_result_revision
Revises: er01_result_dimensions
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "er02_result_revision"
down_revision = "er01_result_dimensions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "emissions_results",
        sa.Column("dataset_revision_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_emissions_results_dataset_revision_id_dataset_revisions",
        "emissions_results",
        "dataset_revisions",
        ["dataset_revision_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_emissions_results_dataset_revision_id", "emissions_results", ["dataset_revision_id"])
    op.add_column(
        "project_dataset_revisions",
        sa.Column("calculation_report", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
    )
    op.execute(sa.text("""
        UPDATE emissions_results er
        SET dataset_revision_id = ad.dataset_revision_id
        FROM activity_data ad
        WHERE ad.id = er.activity_data_id
    """))


def downgrade() -> None:
    op.drop_column("project_dataset_revisions", "calculation_report")
    op.drop_index("ix_emissions_results_dataset_revision_id", table_name="emissions_results")
    op.drop_constraint("fk_emissions_results_dataset_revision_id_dataset_revisions", "emissions_results", type_="foreignkey")
    op.drop_column("emissions_results", "dataset_revision_id")

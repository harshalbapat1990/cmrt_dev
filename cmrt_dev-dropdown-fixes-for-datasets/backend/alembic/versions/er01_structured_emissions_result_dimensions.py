"""add structured reporting dimensions to emissions results

Revision ID: er01_result_dimensions
Revises: dt01_add_rev_id_vehicles
"""
from alembic import op
import sqlalchemy as sa

revision = "er01_result_dimensions"
down_revision = "dt01_add_rev_id_vehicles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("emissions_results", sa.Column("source_category", sa.String(100), nullable=True))
    op.add_column("emissions_results", sa.Column("emissions_scope", sa.String(20), nullable=True))
    op.add_column(
        "emissions_results",
        sa.Column("accounting_basis", sa.String(20), nullable=False, server_default="common"),
    )
    op.add_column(
        "emissions_results",
        sa.Column("reporting_measure", sa.String(20), nullable=False, server_default="actual"),
    )
    op.execute(sa.text("""
        UPDATE emissions_results er
        SET source_category = COALESCE(
                NULLIF(BTRIM(ad.extra_fields->>'emissions_category'), ''),
                CASE WHEN ad.ui_table_key ILIKE '%electricity%' THEN 'Electricity'
                     WHEN ad.ui_table_key IN ('asset','component','constructionG2','constructionG3','bcDetailedLevel') THEN 'Materials'
                     ELSE NULL END
            ),
            emissions_scope = CASE
                WHEN er.value_key ~ '^scope[123]' THEN substring(er.value_key from '^scope([123])')
                ELSE NULL
            END,
            accounting_basis = CASE
                WHEN er.value_key ILIKE '%market%' THEN 'market'
                WHEN er.value_key ILIKE '%location%' THEN 'location'
                ELSE 'common'
            END,
            reporting_measure = CASE
                WHEN NULLIF(BTRIM(ad.extra_fields->>'emissions_category'), '') = 'Offset' THEN 'offset'
                WHEN ad.project_mitigation_id IS NOT NULL OR ad.ui_table_key LIKE '%-mitigation%' THEN 'mitigation'
                ELSE 'actual'
            END
        FROM activity_data ad
        WHERE ad.id = er.activity_data_id
    """))
    op.create_index("ix_emissions_results_reporting", "emissions_results", ["project_id", "project_stage_instance_id", "lifecycle_module_code", "reporting_measure"])
    op.create_index("ix_emissions_results_scope", "emissions_results", ["project_id", "project_stage_instance_id", "emissions_scope", "accounting_basis"])


def downgrade() -> None:
    op.drop_index("ix_emissions_results_scope", table_name="emissions_results")
    op.drop_index("ix_emissions_results_reporting", table_name="emissions_results")
    op.drop_column("emissions_results", "reporting_measure")
    op.drop_column("emissions_results", "accounting_basis")
    op.drop_column("emissions_results", "emissions_scope")
    op.drop_column("emissions_results", "source_category")

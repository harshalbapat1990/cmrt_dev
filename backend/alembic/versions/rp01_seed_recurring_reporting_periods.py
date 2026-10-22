"""seed initial reporting periods for recurring projects

Revision ID: rp01_seed_recurring_periods
Revises: porg01_partner_directory
Create Date: 2026-10-22
"""

from alembic import op


revision = "rp01_seed_recurring_periods"
down_revision = "porg01_partner_directory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Reattach an existing unlinked generated period when it starts at the
    # project's configured first submission month. Projects with any already
    # linked period are left alone.
    op.execute(
        """
        WITH targets AS (
            SELECT
                p.id AS project_id,
                stage_instance.id AS stage_instance_id,
                date_trunc('month', p.first_submission_month)::date AS period_start,
                COALESCE(stage_config.frequency::text, 'MONTHLY') AS frequency
            FROM project p
            JOIN project_stage_instances stage_instance
              ON stage_instance.project_id = p.id
             AND stage_instance.stage::text = 'RECURRING'
            LEFT JOIN project_stage_config stage_config
              ON stage_config.project_id = p.id
             AND stage_config.stage::text = 'CONSTRUCTION'
            WHERE p.project_class::text = 'RECURRING'
              AND p.first_submission_month IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM project_reporting_submission linked
                  WHERE linked.stage_instance_id = stage_instance.id
              )
        ), period_details AS (
            SELECT
                targets.*,
                CASE frequency
                    WHEN 'QUARTERLY' THEN period_start + interval '3 months' - interval '1 day'
                    WHEN 'BI_MONTHLY' THEN period_start + interval '2 months' - interval '1 day'
                    WHEN 'ANNUAL' THEN period_start + interval '1 year' - interval '1 day'
                    ELSE period_start + interval '1 month' - interval '1 day'
                END::date AS period_end,
                CASE frequency
                    WHEN 'QUARTERLY' THEN
                        'Q' || ceil(extract(month FROM period_start) / 3.0)::int || ' ' || extract(year FROM period_start)::int
                    WHEN 'BI_MONTHLY' THEN
                        to_char(period_start, 'Mon YYYY') || ' - ' || to_char(period_start + interval '2 months' - interval '1 day', 'Mon YYYY')
                    WHEN 'ANNUAL' THEN to_char(period_start, 'YYYY')
                    ELSE to_char(period_start, 'Mon YYYY')
                END AS period_label
            FROM targets
        ), reusable AS (
            SELECT DISTINCT ON (details.project_id)
                details.project_id,
                details.stage_instance_id,
                details.frequency,
                details.period_start,
                details.period_end,
                details.period_label,
                unlinked.id AS submission_id
            FROM period_details details
            JOIN project_reporting_submission unlinked
              ON unlinked.project_id = details.project_id
             AND unlinked.stage_instance_id IS NULL
             AND unlinked.period_start_date = details.period_start
            ORDER BY details.project_id, unlinked.id
        )
        UPDATE project_reporting_submission submission
        SET stage_instance_id = reusable.stage_instance_id,
            frequency = reusable.frequency,
            period_start_date = reusable.period_start,
            period_end_date = reusable.period_end,
            period_label = reusable.period_label
        FROM reusable
        WHERE submission.id = reusable.submission_id
        """
    )

    # Insert the first period for recurring projects which have neither a
    # linked period nor a reusable unlinked row for the configured first month.
    op.execute(
        """
        WITH targets AS (
            SELECT
                p.id AS project_id,
                stage_instance.id AS stage_instance_id,
                date_trunc('month', p.first_submission_month)::date AS period_start,
                COALESCE(stage_config.frequency::text, 'MONTHLY') AS frequency
            FROM project p
            JOIN project_stage_instances stage_instance
              ON stage_instance.project_id = p.id
             AND stage_instance.stage::text = 'RECURRING'
            LEFT JOIN project_stage_config stage_config
              ON stage_config.project_id = p.id
             AND stage_config.stage::text = 'CONSTRUCTION'
            WHERE p.project_class::text = 'RECURRING'
              AND p.first_submission_month IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM project_reporting_submission linked
                  WHERE linked.stage_instance_id = stage_instance.id
              )
              AND NOT EXISTS (
                  SELECT 1
                  FROM project_reporting_submission unlinked
                  WHERE unlinked.project_id = p.id
                    AND unlinked.stage_instance_id IS NULL
                    AND unlinked.period_start_date = date_trunc('month', p.first_submission_month)::date
              )
        ), period_details AS (
            SELECT
                targets.*,
                CASE frequency
                    WHEN 'QUARTERLY' THEN period_start + interval '3 months' - interval '1 day'
                    WHEN 'BI_MONTHLY' THEN period_start + interval '2 months' - interval '1 day'
                    WHEN 'ANNUAL' THEN period_start + interval '1 year' - interval '1 day'
                    ELSE period_start + interval '1 month' - interval '1 day'
                END::date AS period_end,
                CASE frequency
                    WHEN 'QUARTERLY' THEN
                        'Q' || ceil(extract(month FROM period_start) / 3.0)::int || ' ' || extract(year FROM period_start)::int
                    WHEN 'BI_MONTHLY' THEN
                        to_char(period_start, 'Mon YYYY') || ' - ' || to_char(period_start + interval '2 months' - interval '1 day', 'Mon YYYY')
                    WHEN 'ANNUAL' THEN to_char(period_start, 'YYYY')
                    ELSE to_char(period_start, 'Mon YYYY')
                END AS period_label
            FROM targets
        )
        INSERT INTO project_reporting_submission (
            project_id,
            stage_instance_id,
            frequency,
            period_label,
            period_start_date,
            period_end_date,
            status
        )
        SELECT
            project_id,
            stage_instance_id,
            frequency,
            period_label,
            period_start,
            period_end,
            'in_progress'
        FROM period_details
        """
    )


def downgrade() -> None:
    # This data-only migration reuses existing orphan period rows as well as
    # inserting new ones. Keep the rows on downgrade to avoid losing reports.
    pass

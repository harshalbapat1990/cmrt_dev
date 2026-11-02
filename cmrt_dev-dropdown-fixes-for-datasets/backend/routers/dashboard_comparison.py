"""
routers/dashboard_comparison.py

Dashboard Results API — Comparison by Stage / Period

Three endpoints
──────────────────────────────────────────────────────────────────────────────
  GET /by-submission            — stacked-column data: total emissions broken
                                  down by data grade (1/2/3/4) for every stage
                                  submission of the project

  GET /by-construction-period   — line-graph data: total emissions per
                                  construction reporting period

  GET /detail                   — row-level breakdown across all grades/stages

Electricity accounting
──────────────────────────────────────────────────────────────────────────────
  All endpoints accept an optional `elec_method` query parameter:
    'location'  (default)  → aggregates common and location-basis result facts
    'market'               → aggregates common and market-basis result facts

Grade definitions
──────────────────────────────────────────────────────────────────────────────
  Grade 1  — ui_table_key = 'asset'
             source: emissions_results

  Grade 2  — ui_table_key IN ('component', 'componentRepl', 'useB1G2')
             source: emissions_results
           — ui_table_key = 'opEnergy'
             field: location_based_total_tco2e / market_based_total_tco2e
             source: emissions_results

  Grade 3  — Construction stage:
               ui_table_key IN ('bcDetailedLevel', 'constructionG3')
               WHERE extra_fields->>'data_quality' = 'Estimated'
               field: total_emissions_tco2e
           — Non-construction stages:
               ui_table_key IN ('bcDetailedLevel', 'replDetailed',
                                'useB1G3', 'opEnergyDetailed')
               field: total_emissions_tco2e
           — Electricity (all stages, Estimated or non-construction):
               ui_table_key IN ('electricity', 'opEnergyElectricity')
               field: location_based_tco2e / market_based_tco2e

  Grade 4  — Construction stage only:
               same construction tables WHERE data_quality = 'Monitored'
               field: total_emissions_tco2e / location_based_tco2e / market_based_tco2e

Query params
──────────────────────────────────────────────────────────────────────────────
  project_id         UUID  required
  stage_instance_id  UUID  optional (detail endpoint only)
  elec_method        str   optional — 'location' (default) | 'market'
"""

from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from services._calc_utils import DashboardBase
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session

router = APIRouter(
    prefix="/api/dashboard/comparison",
    tags=["Dashboard - Comparison by Stage/Period"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Response models
# ─────────────────────────────────────────────────────────────────────────────


class SubmissionGrades(DashboardBase):
    grade1: Decimal
    grade2: Decimal
    grade3: Decimal
    grade4: Decimal


class SubmissionRow(DashboardBase):
    stage_instance_id: str
    label: str
    stage: str
    grades: SubmissionGrades
    total: Decimal


class ComparisonBySubmissionResponse(DashboardBase):
    unit: str
    submissions: List[SubmissionRow]


class ConstructionPeriodRow(DashboardBase):
    period_label: str
    total_tco2e: Decimal


class ComparisonByConstructionPeriodResponse(DashboardBase):
    unit: str
    stage: str
    periodicity: Optional[str]
    periods: List[ConstructionPeriodRow]


class ComparisonDetailRow(DashboardBase):
    stage_label: str
    stage: str
    grade: str
    data_source: str
    emissions_source: Optional[str]
    emissions_category: Optional[str]
    unit_code: Optional[str]
    total_tco2e: Decimal


class ComparisonDetailResponse(DashboardBase):
    rows: List[ComparisonDetailRow]


# ─────────────────────────────────────────────────────────────────────────────
# SQL — by-submission (stacked column data)
# ─────────────────────────────────────────────────────────────────────────────

_BY_SUBMISSION_SQL = text("""
WITH
-- All stage instances for this project
si AS (
    SELECT id, stage::text AS stage, sequence
    FROM project_stage_instances
    WHERE project_id = CAST(:project_id AS uuid)
),

-- Grade 1: Construction Asset Level table
g1 AS (
    SELECT ad.project_stage_instance_id AS si_id,
           SUM(COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END)), 0))
               AS tco2e
    FROM activity_data ad
    WHERE ad.project_id = CAST(:project_id AS uuid)
      AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND ad.ui_table_key = 'asset'
    GROUP BY ad.project_stage_instance_id
),

-- Grade 2: non-electricity component level
g2_component AS (
    SELECT ad.project_stage_instance_id AS si_id,
           SUM(COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END)), 0))
               AS tco2e
    FROM activity_data ad
    WHERE ad.project_id = CAST(:project_id AS uuid)
      AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND ad.ui_table_key IN ('component', 'componentRepl', 'useB1G2')
    GROUP BY ad.project_stage_instance_id
),

-- Grade 2: operational energy component level (electricity-aware)
g2_op_energy AS (
    SELECT ad.project_stage_instance_id AS si_id,
           SUM(
               CASE WHEN :elec_method = 'market'
                   THEN COALESCE(
                       (SELECT COALESCE(SUM(er.value), 0) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END)),
                       (SELECT COALESCE(SUM(er.value), 0) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END)),
                       0
                   )
                   ELSE COALESCE(
                       (SELECT COALESCE(SUM(er.value), 0) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END)),
                       (SELECT COALESCE(SUM(er.value), 0) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END)),
                       0
                   )
               END
           ) AS tco2e
    FROM activity_data ad
    WHERE ad.project_id = CAST(:project_id AS uuid)
      AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND ad.ui_table_key = 'opEnergy'
    GROUP BY ad.project_stage_instance_id
),

-- Grade 3: non-electricity detailed level
--   Construction stage : bcDetailedLevel / constructionG3 WHERE data_quality = 'Estimated'
--   All other stages   : bcDetailedLevel / replDetailed / useB1G3 / opEnergyDetailed
g3_detailed AS (
    SELECT ad.project_stage_instance_id AS si_id,
           SUM(COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END)), 0))
               AS tco2e
    FROM activity_data ad
    JOIN si ON si.id = ad.project_stage_instance_id
    WHERE ad.project_id = CAST(:project_id AS uuid)
      AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND (
          (   si.stage = 'CONSTRUCTION'
           AND ad.ui_table_key IN ('bcDetailedLevel', 'constructionG3')
           AND ad.extra_fields->>'data_quality' = 'Estimated')
          OR
          (   si.stage <> 'CONSTRUCTION'
           AND ad.ui_table_key IN ('bcDetailedLevel', 'replDetailed', 'useB1G3', 'opEnergyDetailed'))
      )
    GROUP BY ad.project_stage_instance_id
),

-- Grade 3: electricity (electricity-aware)
--   Construction: WHERE data_quality = 'Estimated'
--   Non-construction: all rows
g3_electricity AS (
    SELECT ad.project_stage_instance_id AS si_id,
           SUM(
               CASE WHEN :elec_method = 'market'
                   THEN (SELECT COALESCE(SUM(er.value), 0) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END))
                   ELSE COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END)), 0)
               END
           ) AS tco2e
    FROM activity_data ad
    JOIN si ON si.id = ad.project_stage_instance_id
    WHERE ad.project_id = CAST(:project_id AS uuid)
      AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND ad.ui_table_key IN ('electricity', 'opEnergyElectricity')
      AND (
          si.stage <> 'CONSTRUCTION'
          OR ad.extra_fields->>'data_quality' = 'Estimated'
      )
    GROUP BY ad.project_stage_instance_id
),

-- Grade 4: construction stage only, data_quality = 'Monitored' (non-electricity)
g4_detailed AS (
    SELECT ad.project_stage_instance_id AS si_id,
           SUM(COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END)), 0))
               AS tco2e
    FROM activity_data ad
    JOIN si ON si.id = ad.project_stage_instance_id
    WHERE ad.project_id = CAST(:project_id AS uuid)
      AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND si.stage = 'CONSTRUCTION'
      AND ad.ui_table_key IN ('bcDetailedLevel', 'constructionG3')
      AND ad.extra_fields->>'data_quality' = 'Monitored'
    GROUP BY ad.project_stage_instance_id
),

-- Grade 4: construction electricity, data_quality = 'Monitored'
g4_electricity AS (
    SELECT ad.project_stage_instance_id AS si_id,
           SUM(
               CASE WHEN :elec_method = 'market'
                   THEN (SELECT COALESCE(SUM(er.value), 0) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END))
                   ELSE COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END)), 0)
               END
           ) AS tco2e
    FROM activity_data ad
    JOIN si ON si.id = ad.project_stage_instance_id
    WHERE ad.project_id = CAST(:project_id AS uuid)
      AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND si.stage = 'CONSTRUCTION'
      AND ad.ui_table_key IN ('electricity', 'opEnergyElectricity')
      AND ad.extra_fields->>'data_quality' = 'Monitored'
    GROUP BY ad.project_stage_instance_id
)

SELECT
    si.id::text                                                          AS stage_instance_id,
    si.stage,
    si.sequence,
    CASE si.stage
        WHEN 'BUSINESS_CASE' THEN 'Business Case'
        WHEN 'DESIGN'        THEN 'Design'
        WHEN 'CONSTRUCTION'  THEN 'Construction'
        WHEN 'RECURRING'     THEN 'Recurring'
        ELSE si.stage
    END                                                                  AS label,
    COALESCE(g1.tco2e,   0)                                             AS grade1_tco2e,
    COALESCE(g2c.tco2e,  0) + COALESCE(g2e.tco2e,  0)                  AS grade2_tco2e,
    COALESCE(g3d.tco2e,  0) + COALESCE(g3el.tco2e, 0)                  AS grade3_tco2e,
    COALESCE(g4d.tco2e,  0) + COALESCE(g4el.tco2e, 0)                  AS grade4_tco2e
FROM si
LEFT JOIN g1           ON g1.si_id   = si.id
LEFT JOIN g2_component g2c ON g2c.si_id  = si.id
LEFT JOIN g2_op_energy g2e ON g2e.si_id  = si.id
LEFT JOIN g3_detailed  g3d ON g3d.si_id  = si.id
LEFT JOIN g3_electricity g3el ON g3el.si_id = si.id
LEFT JOIN g4_detailed  g4d ON g4d.si_id  = si.id
LEFT JOIN g4_electricity g4el ON g4el.si_id = si.id
ORDER BY si.sequence
""")


# ─────────────────────────────────────────────────────────────────────────────
# SQL — by-construction-period (line graph data)
# ─────────────────────────────────────────────────────────────────────────────

_BY_CONSTRUCTION_PERIOD_SQL = text("""
WITH
construction_si AS (
    SELECT id
    FROM project_stage_instances
    WHERE project_id = CAST(:project_id AS uuid)
      AND stage::text = 'CONSTRUCTION'
),
period_totals AS (
    SELECT
        prs.id                AS period_id,
        prs.period_label,
        prs.period_start_date,
        prs.frequency,
        SUM(
            CASE
                -- Grade 2: non-electricity
                WHEN ad.ui_table_key IN ('component', 'componentRepl', 'useB1G2')
                    THEN COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END)), 0)

                -- Grade 3: detailed non-electricity (Estimated only)
                WHEN ad.ui_table_key IN ('bcDetailedLevel', 'constructionG3')
                     AND COALESCE(ad.extra_fields->>'data_quality', '') = 'Estimated'
                    THEN COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END)), 0)

                -- Grade 4: detailed non-electricity (Monitored only)
                WHEN ad.ui_table_key IN ('bcDetailedLevel', 'constructionG3')
                     AND COALESCE(ad.extra_fields->>'data_quality', '') = 'Monitored'
                    THEN COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END)), 0)

                -- Grade 2: opEnergy electricity
                WHEN ad.ui_table_key = 'opEnergy'
                    THEN CASE WHEN :elec_method = 'market'
                             THEN COALESCE(
                                 (SELECT COALESCE(SUM(er.value), 0) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END)),
                                 (SELECT COALESCE(SUM(er.value), 0) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END)),
                                 0
                             )
                             ELSE COALESCE(
                                 (SELECT COALESCE(SUM(er.value), 0) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END)),
                                 (SELECT COALESCE(SUM(er.value), 0) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END)),
                                 0
                             )
                         END

                -- Grade 3: electricity (Estimated only)
                WHEN ad.ui_table_key IN ('electricity', 'opEnergyElectricity')
                     AND COALESCE(ad.extra_fields->>'data_quality', '') = 'Estimated'
                    THEN CASE WHEN :elec_method = 'market'
                             THEN (SELECT COALESCE(SUM(er.value), 0) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END))
                             ELSE COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END)), 0)
                         END

                -- Grade 4: electricity (Monitored only)
                WHEN ad.ui_table_key IN ('electricity', 'opEnergyElectricity')
                     AND COALESCE(ad.extra_fields->>'data_quality', '') = 'Monitored'
                    THEN CASE WHEN :elec_method = 'market'
                             THEN (SELECT COALESCE(SUM(er.value), 0) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END))
                             ELSE COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END)), 0)
                         END

                ELSE 0
            END
        ) AS total_tco2e
    FROM activity_data ad
    JOIN construction_si csi ON csi.id = ad.project_stage_instance_id
    JOIN project_reporting_submission prs ON prs.id = ad.submission_period_id
    WHERE ad.project_id = CAST(:project_id AS uuid)
      AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND ad.ui_table_key IN (
          'component', 'componentRepl', 'useB1G2', 'opEnergy',
          'bcDetailedLevel', 'constructionG3', 'electricity', 'opEnergyElectricity'
      )
    GROUP BY prs.id, prs.period_label, prs.period_start_date, prs.frequency
)
SELECT period_label, period_start_date, frequency, total_tco2e
FROM period_totals
ORDER BY period_start_date NULLS LAST, period_label
""")


# ─────────────────────────────────────────────────────────────────────────────
# SQL — detail (row-level breakdown)
# ─────────────────────────────────────────────────────────────────────────────

_DETAIL_SQL = text("""
SELECT
    CASE si.stage::text
        WHEN 'BUSINESS_CASE' THEN 'Business Case'
        WHEN 'DESIGN'        THEN 'Design'
        WHEN 'CONSTRUCTION'  THEN 'Construction'
        WHEN 'RECURRING'     THEN 'Recurring'
        ELSE si.stage::text
    END                                                                     AS stage_label,
    si.stage::text                                                           AS stage,
    CASE
        WHEN ad.ui_table_key = 'asset'
            THEN 'Grade 1'
        WHEN ad.ui_table_key IN ('component', 'componentRepl', 'useB1G2', 'opEnergy')
            THEN 'Grade 2'
        WHEN si.stage::text = 'CONSTRUCTION'
             AND ad.ui_table_key IN ('bcDetailedLevel', 'constructionG3',
                                     'electricity', 'opEnergyElectricity')
             AND ad.extra_fields->>'data_quality' = 'Monitored'
            THEN 'Grade 4'
        ELSE 'Grade 3'
    END                                                                      AS grade,
    ad.ui_table_key                                                          AS data_source,
    COALESCE(
        NULLIF(ad.extra_fields->>'emissions_source_name', ''),
        NULLIF(ad.extra_fields->>'emissions_source',      ''),
        '(unspecified)'
    )                                                                        AS emissions_source,
    COALESCE(NULLIF(ad.extra_fields->>'emissions_category', ''), '(unspecified)')
                                                                             AS emissions_category,
    COALESCE(ad.extra_fields->>'unit_code', '')                              AS unit_code,
    CASE
        WHEN ad.ui_table_key = 'opEnergy'
            THEN CASE WHEN :elec_method = 'market'
                     THEN COALESCE(
                         (SELECT COALESCE(SUM(er.value), 0) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END)),
                         (SELECT COALESCE(SUM(er.value), 0) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END)),
                         0
                     )
                     ELSE COALESCE(
                         (SELECT COALESCE(SUM(er.value), 0) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END)),
                         (SELECT COALESCE(SUM(er.value), 0) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END)),
                         0
                     )
                 END
        WHEN ad.ui_table_key IN ('electricity', 'opEnergyElectricity')
            THEN CASE WHEN :elec_method = 'market'
                     THEN (SELECT COALESCE(SUM(er.value), 0) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END))
                     ELSE COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END)), 0)
                 END
        ELSE COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END)), 0)
    END                                                                      AS total_tco2e
FROM activity_data ad
JOIN project_stage_instances si ON si.id = ad.project_stage_instance_id
WHERE ad.project_id = CAST(:project_id AS uuid)
  AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
  AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
  AND (NOT :filter_by_stage OR ad.project_stage_instance_id = CAST(:stage_instance_id AS uuid))
  AND ad.ui_table_key IN (
      'asset', 'component', 'componentRepl', 'useB1G2', 'opEnergy',
      'bcDetailedLevel', 'constructionG3', 'replDetailed', 'useB1G3',
      'opEnergyDetailed', 'electricity', 'opEnergyElectricity'
  )
ORDER BY si.sequence, grade, emissions_category, emissions_source
""")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _base_params(
    project_id: UUID,
    elec_method: str,
    project_option_id: Optional[UUID] = None,
    submission_period_id: Optional[UUID] = None,
) -> dict:
    return {
        "project_id": str(project_id),
        "elec_method": elec_method,
        "project_option_id": str(project_option_id) if project_option_id else None,
        "submission_period_id": str(submission_period_id) if submission_period_id else None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/by-submission",
    response_model=ComparisonBySubmissionResponse,
    status_code=status.HTTP_200_OK,
    summary="Comparison by stage — emissions by data grade per submission",
    description=(
        "Returns total emissions broken down by data grade (Grade 1/2/3/4) for every "
        "stage submission of the project. Drives the stacked column chart on the left. "
        "\n\nGrade 4 is only populated for the Construction stage "
        "(rows where `data_quality = 'Monitored'`)."
    ),
)
async def get_by_submission(
    project_id: UUID = Query(..., description="Project UUID"),
    elec_method: str = Query("location", description="Electricity method: 'location' or 'market'"),
    project_option_id: Optional[UUID] = Query(None, description="Project option UUID (optional filter)"),
    submission_period_id: Optional[UUID] = Query(None, description="Submission period UUID (optional filter)"),
    db: AsyncSession = Depends(get_session),
) -> ComparisonBySubmissionResponse:
    params = _base_params(project_id, elec_method, project_option_id, submission_period_id)

    try:
        result = await db.execute(_BY_SUBMISSION_SQL, params)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {exc}",
        )

    submissions = []
    for row in result.mappings().all():
        g1 = row.grade1_tco2e or Decimal("0")
        g2 = row.grade2_tco2e or Decimal("0")
        g3 = row.grade3_tco2e or Decimal("0")
        g4 = row.grade4_tco2e or Decimal("0")
        submissions.append(
            SubmissionRow(
                stage_instance_id=row.stage_instance_id,
                label=row.label,
                stage=row.stage,
                grades=SubmissionGrades(grade1=g1, grade2=g2, grade3=g3, grade4=g4),
                total=g1 + g2 + g3 + g4,
            )
        )

    return ComparisonBySubmissionResponse(unit="tCO2e", submissions=submissions)


@router.get(
    "/by-construction-period",
    response_model=ComparisonByConstructionPeriodResponse,
    status_code=status.HTTP_200_OK,
    summary="Comparison by construction period — total emissions per reporting period",
    description=(
        "Returns total emissions for each construction reporting period. "
        "Drives the line graph on the right. "
        "Only includes data linked to Construction stage instances via `submission_period_id`."
    ),
)
async def get_by_construction_period(
    project_id: UUID = Query(..., description="Project UUID"),
    elec_method: str = Query("location", description="Electricity method: 'location' or 'market'"),
    project_option_id: Optional[UUID] = Query(None, description="Project option UUID (optional filter)"),
    submission_period_id: Optional[UUID] = Query(None, description="Submission period UUID (optional filter)"),
    db: AsyncSession = Depends(get_session),
) -> ComparisonByConstructionPeriodResponse:
    params = _base_params(project_id, elec_method, project_option_id, submission_period_id)

    try:
        result = await db.execute(_BY_CONSTRUCTION_PERIOD_SQL, params)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {exc}",
        )

    rows_raw = result.mappings().all()
    periods = [
        ConstructionPeriodRow(
            period_label=row.period_label,
            total_tco2e=row.total_tco2e or Decimal("0"),
        )
        for row in rows_raw
    ]

    periodicity = rows_raw[0].frequency if rows_raw else None

    return ComparisonByConstructionPeriodResponse(
        unit="tCO2e",
        stage="Construction",
        periodicity=periodicity,
        periods=periods,
    )


@router.get(
    "/detail",
    response_model=ComparisonDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Comparison detail — row-level emissions breakdown across all grades and stages",
    description=(
        "Returns every individual activity_data row contributing to the comparison totals, "
        "annotated with stage, grade, data source, category, source name, unit and tCO₂e. "
        "\n\nOptionally filter to a single stage instance via `stage_instance_id`."
    ),
)
async def get_detail(
    project_id: UUID = Query(..., description="Project UUID"),
    stage_instance_id: Optional[UUID] = Query(None, description="Stage instance UUID (optional)"),
    elec_method: str = Query("location", description="Electricity method: 'location' or 'market'"),
    project_option_id: Optional[UUID] = Query(None, description="Project option UUID (optional filter)"),
    submission_period_id: Optional[UUID] = Query(None, description="Submission period UUID (optional filter)"),
    db: AsyncSession = Depends(get_session),
) -> ComparisonDetailResponse:
    params = {
        **_base_params(project_id, elec_method, project_option_id, submission_period_id),
        "filter_by_stage": stage_instance_id is not None,
        "stage_instance_id": str(stage_instance_id) if stage_instance_id else "00000000-0000-0000-0000-000000000000",
    }

    try:
        result = await db.execute(_DETAIL_SQL, params)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {exc}",
        )

    rows = [
        ComparisonDetailRow(
            stage_label=row.stage_label,
            stage=row.stage,
            grade=row.grade,
            data_source=row.data_source,
            emissions_source=row.emissions_source,
            emissions_category=row.emissions_category,
            unit_code=row.unit_code,
            total_tco2e=row.total_tco2e or Decimal("0"),
        )
        for row in result.mappings().all()
    ]

    return ComparisonDetailResponse(rows=rows)

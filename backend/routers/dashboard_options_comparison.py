"""
routers/dashboard_options_comparison.py

Dashboard Results API — Options Comparison

Compares total A1–B8 emissions and carbon value across all project options
for the BUSINESS_CASE stage.

─────────────────────────────────────────────────────────────────────────────
Response format (matches frontend ComparisonByOption component)
─────────────────────────────────────────────────────────────────────────────

{
  "unit": { "emissions": "tCO2e", "carbonValue": "AUD 2023" },
  "projectOptions": [
    {
      "label": "Business case - option 1",
      "emissions":   { "min": <low>, "medium": <central>, "max": <high> },
      "carbonValue": { "min": <low>, "medium": <central>, "max": <high> }
    },
    ...
  ]
}

  emissions.min/medium/max   — same total A1–B8 tCO₂e value, repeated per
                               range row so the table can pair with carbon values
  carbonValue.min/medium/max — total_a1_b8_tco2e × carbon_price_for_range
  min=low, medium=central, max=high (frontend displays Minimum/Medium/Maximum)

─────────────────────────────────────────────────────────────────────────────
Query params
─────────────────────────────────────────────────────────────────────────────
  project_id   UUID  required
  elec_method  str   optional — 'location' (default) | 'market'
"""

import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from services._calc_utils import DashboardBase
from services.project_context_helper import ProjectContextHelper
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from routers.dashboard_emissions_breakdown import _MODULE_META

router = APIRouter(
    prefix="/api/dashboard/options-comparison",
    tags=["Dashboard - Options Comparison"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Response models
# ─────────────────────────────────────────────────────────────────────────────

class EmissionsRange(DashboardBase):
    """Total A1–B8 tCO₂e for one option across the three carbon price ranges.
    min=low, medium=central, max=high — names match the frontend keys."""
    min: Decimal
    medium: Decimal
    max: Decimal


class CarbonValueRange(DashboardBase):
    """Carbon value (currency) for one option across the three ranges."""
    min: Decimal
    medium: Decimal
    max: Decimal


class ProjectOptionData(DashboardBase):
    """Emissions and carbon value data for one project option."""
    label: str
    emissions: EmissionsRange
    carbonValue: CarbonValueRange


class UnitInfo(DashboardBase):
    """Unit labels shown in the table headers."""
    emissions: str = "tCO2e"
    carbonValue: str = ""


class OptionsComparisonResponse(DashboardBase):
    """Full response for the Options Comparison dashboard tab.

    Matches the frontend ComparisonByOption component's expected shape:
      { unit: { emissions, carbonValue }, projectOptions: [...] }
    """
    unit: UnitInfo
    projectOptions: List[ProjectOptionData]


# ─────────────────────────────────────────────────────────────────────────────
# SQL — per-option module breakdown
#
# Identical logic to _MODULE_SQL in dashboard_emissions_breakdown.py, with
# one addition: every WHERE clause includes AND project_option_id = :option_id
# to isolate rows belonging to the specific project option being calculated.
# ─────────────────────────────────────────────────────────────────────────────

_OPTION_MODULE_SQL = text("""
WITH

-- ════════════════════════════════════════════════════════════════════════════
-- TIER 1 — emissions_results JOIN (canonical per-module tCO2e values)
--
-- Same logic as dashboard_emissions_breakdown._MODULE_SQL with the addition
-- of AND project_option_id = :option_id on every activity_data filter.
-- ════════════════════════════════════════════════════════════════════════════

er_a1a3 AS (
    -- All input levels (Grade 1 asset, Grade 2 component, Grade 3/4 detailed).
    -- The developer stores the correct A1-A3 split in emissions_results.
    SELECT COALESCE(SUM(er.value), 0) AS val
    FROM activity_data ad
    JOIN emissions_results er ON er.activity_data_id = ad.id
        AND er.value_key = 'A1-A3'
    WHERE ad.project_id                = :project_id
      AND ad.project_stage_instance_id = :stage_instance_id
      AND ad.project_option_id         = :option_id
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
),

-- ── Grade 3/4 Materials rows: A1-A3 and A4 splits ───────────────────────────────────────────
-- bcDetailedLevel / constructionG3: reads pre-computed values from emissions_results
--   (written by recalc_grade34_construction_activity_row when activity is saved).
-- recurringG3: kept on old runtime-join path until migrated.
g34_mat_splits AS (
    -- bcDetailedLevel / constructionG3: read from emissions_results (no view join needed)
    SELECT
        COALESCE(er_a1a3.value, 0) AS a1_a3,
        COALESCE(er_a4.value,   0) AS a4
    FROM activity_data ad
    LEFT JOIN emissions_results er_a1a3
        ON  er_a1a3.activity_data_id = ad.id
        AND er_a1a3.value_key = 'A1-A3'
        AND NOT er_a1a3.is_supplementary
    LEFT JOIN emissions_results er_a4
        ON  er_a4.activity_data_id = ad.id
        AND er_a4.value_key = 'A4'
        AND NOT er_a4.is_supplementary
    WHERE ad.project_id                = :project_id
      AND ad.project_stage_instance_id = :stage_instance_id
      AND ad.project_option_id         = :option_id
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND ad.ui_table_key IN ('bcDetailedLevel', 'constructionG3')
      AND ad.extra_fields->>'emissions_category' = 'Materials'

    UNION ALL

    -- recurringG3: legacy runtime-join path (not yet migrated to emissions_results)
    SELECT
        LEAST(
            COALESCE(ef.emission_factor_scope3, 0) * ad.quantity,
            COALESCE(NULLIF(NULLIF(ad.extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)
        ) AS a1_a3,
        GREATEST(0,
            COALESCE(NULLIF(NULLIF(ad.extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0) -
            COALESCE(ef.emission_factor_scope3, 0) * ad.quantity
        ) AS a4
    FROM activity_data ad
    LEFT JOIN v_grade34_detailed_level ef
        ON  ef."Jurisdiction"     = :jurisdiction
        AND ef."Emissions Source" = COALESCE(NULLIF(ad.extra_fields->>'emissions_source_name', ''), '__no_match__')
        AND ef."UoM"              = COALESCE(NULLIF(ad.extra_fields->>'unit_code', ''), '__no_match__')
    WHERE ad.project_id                = :project_id
      AND ad.project_stage_instance_id = :stage_instance_id
      AND ad.project_option_id         = :option_id
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND ad.ui_table_key = 'recurringG3'
      AND ad.extra_fields->>'emissions_category' = 'Materials'
),

er_a4 AS (
    -- Grade 3/4 Materials A4 (bcDetailedLevel/constructionG3 from emissions_results;
    -- recurringG3 legacy view-join) plus Grade 1 asset and Grade 2 component A4
    -- stored in emissions_results by recalc_asset_row / recalc_grade2_component_row.
    SELECT
        COALESCE((SELECT SUM(a4) FROM g34_mat_splits), 0)
        +
        COALESCE((
            SELECT SUM(er.value)
            FROM activity_data ad
            JOIN emissions_results er ON er.activity_data_id = ad.id
                AND er.value_key = 'A4'
                AND NOT er.is_supplementary
            WHERE ad.project_id                = :project_id
              AND ad.project_stage_instance_id = :stage_instance_id
              AND ad.project_option_id         = :option_id
              AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
              AND ad.ui_table_key IN ('asset', 'component')
        ), 0) AS val
),

er_a5 AS (
    -- Grade 1 / Grade 2 / Grade 3-4 A5: rows with value_key = 'A5' in emissions_results.
    -- Excludes electricity rows (ui_table_key='electricity') — those are handled by
    -- a5_elec which reads extra_fields location/market totals directly.
    SELECT COALESCE(SUM(er.value), 0) AS val
    FROM activity_data ad
    JOIN emissions_results er ON er.activity_data_id = ad.id
        AND er.value_key = 'A5'
    WHERE ad.project_id                = :project_id
      AND ad.project_stage_instance_id = :stage_instance_id
      AND ad.project_option_id         = :option_id
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND ad.ui_table_key NOT LIKE 'electricity%'
),

a5_elec AS (
    -- Construction electricity (ui_table_key='electricity').
    -- Design and Construction stages only (no electricity rows in Business Case).
    -- location_based_tco2e / market_based_tco2e from extra_fields (Scope 2+3 totals).
    SELECT COALESCE(SUM(
        CASE WHEN :elec_method = 'market'
             THEN COALESCE(NULLIF(NULLIF(extra_fields->>'market_based_tco2e',   ''), '-')::numeric, 0)
             ELSE COALESCE(NULLIF(NULLIF(extra_fields->>'location_based_tco2e', ''), '-')::numeric, 0)
        END
    ), 0) AS val
    FROM activity_data
    WHERE project_id                = :project_id
      AND project_stage_instance_id = :stage_instance_id
      AND project_option_id         = :option_id
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'electricity'
),

a5_sat4p AS (
    -- Shortcut SAT4P A5: only the 3 A5-specific sources.
    -- 'Construction materials' → A1-A3, 'Transport (construction materials)' → A4,
    -- 'Maintenance processes / equipment' / 'Transport (maintenance materials)' → B2-B5,
    -- 'Use phase' → B8 — all excluded by using an explicit IN list.
    SELECT COALESCE(SUM(
        COALESCE(NULLIF(NULLIF(extra_fields->>'actual_scope3', ''), '-')::numeric, 0) +
        COALESCE(NULLIF(NULLIF(extra_fields->>'actual_scope4', ''), '-')::numeric, 0)
    ), 0) AS val
    FROM activity_data
    WHERE project_id                = :project_id
      AND project_stage_instance_id = :stage_instance_id
      AND project_option_id         = :option_id
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'shortcutSat4p'
      AND extra_fields->>'source' IN (
          'Construction processes/equipment',
          'Disposal',
          'Transport off-site (waste)'
      )
),

b2_b5 AS (
    -- B2-B5: three ui_table_keys covering all input grades.
    --   componentRepl  → Component Level Replacement (B4) (Grade 2 and 3)
    --   refurbishment  → Other Maintenance/Repair/Replacement/Refurbishment Activities (Grade 2)
    --   replDetailed   → Detailed Level (Grade 3)  [Offset rows excluded — handled by offsets CTE]
    SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)), 0) AS val
    FROM activity_data
    WHERE project_id                = :project_id
      AND project_stage_instance_id = :stage_instance_id
      AND project_option_id         = :option_id
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key IN ('componentRepl', 'refurbishment', 'replDetailed')
      AND NOT (ui_table_key = 'replDetailed' AND COALESCE(extra_fields->>'emissions_category', '') = 'Offset')
),

er_b6_elec AS (
    -- Operational electricity (ui_table_key='opEnergyElectricity').
    -- Uses location_based_tco2e / market_based_tco2e from extra_fields (Scope 2+3 totals).
    SELECT COALESCE(SUM(
        CASE WHEN :elec_method = 'market'
             THEN COALESCE(NULLIF(NULLIF(extra_fields->>'market_based_tco2e',   ''), '-')::numeric, 0)
             ELSE COALESCE(NULLIF(NULLIF(extra_fields->>'location_based_tco2e', ''), '-')::numeric, 0)
        END
    ), 0) AS val
    FROM activity_data
    WHERE project_id                = :project_id
      AND project_stage_instance_id = :stage_instance_id
      AND project_option_id         = :option_id
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'opEnergyElectricity'
),

-- ════════════════════════════════════════════════════════════════════════════
-- TIER 2 — modules not yet in lifecycle_modules (extra_fields fallback)
-- ════════════════════════════════════════════════════════════════════════════

b1 AS (
    SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND project_option_id = :option_id
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key IN ('useB1G2', 'useB1G3')
),

b6_op AS (
    -- Component Level (Grade 2): use operational total based on elec_method.
    -- Prefer method-specific total, with total_emissions_tco2e as fallback.
    SELECT COALESCE(SUM(
        CASE WHEN :elec_method = 'market'
             THEN COALESCE(
                     NULLIF(NULLIF(extra_fields->>'market_based_total_tco2e', ''), '-')::numeric,
                     COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)
                  )
             ELSE COALESCE(
                     NULLIF(NULLIF(extra_fields->>'location_based_total_tco2e', ''), '-')::numeric,
                     COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)
                  )
        END
    ), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND project_option_id = :option_id
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'opEnergy'
),

b6_detailed AS (
    -- opEnergyDetailed non-Water, non-Offset rows (Offset rows are captured in the offsets CTE)
    SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND project_option_id = :option_id
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'opEnergyDetailed'
      AND COALESCE(extra_fields->>'emissions_category', '') NOT IN ('Water', 'Offset')
),

b7 AS (
    SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND project_option_id = :option_id
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'opEnergyDetailed'
      AND extra_fields->>'emissions_category' = 'Water'
),

b8_road AS (
    -- Small project road users: relativeUserEmissions
    SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'relativeUserEmissions', ''), '-')::numeric, 0)), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND project_option_id = :option_id
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'roadUsers'
),

b8_rail AS (
    -- Rail users (small and large): emissions_total_ref_period_tco2e
    SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'emissions_total_ref_period_tco2e', ''), '-')::numeric, 0)), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND project_option_id = :option_id
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'railUsers'
),

b8_large_road AS (
    -- Large project road users: final_user_emissions_tco2e from largeRoadParams.
    -- This value repeats across modelled years for the same parameter combination
    -- (gradient / curvature / roughness / ev_uptake_scenario).
    -- Deduplicate: take MAX per unique combination, then sum across combinations.
    SELECT COALESCE(SUM(max_val), 0) AS val
    FROM (
        SELECT MAX(COALESCE(NULLIF(NULLIF(extra_fields->>'final_user_emissions_tco2e', ''), '-')::numeric, 0)) AS max_val
        FROM activity_data
        WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
          AND project_option_id = :option_id
          AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
          AND ui_table_key = 'largeRoadParams'
        GROUP BY
            extra_fields->>'gradient',
            extra_fields->>'curvature',
            extra_fields->>'roughness',
            extra_fields->>'ev_uptake_scenario'
    ) d
),

b8 AS (
    SELECT (SELECT val FROM b8_road) + (SELECT val FROM b8_rail) + (SELECT val FROM b8_large_road) AS val
),

offsets AS (
    SELECT -COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND project_option_id = :option_id
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key IN (
          'bcDetailedLevel', 'constructionG3', 'recurringG3',
          'replDetailed', 'opEnergyDetailed'
      )
      AND extra_fields->>'emissions_category' = 'Offset'
),

-- ════════════════════════════════════════════════════════════════════════════
-- TIER 3 — completeness upscaling adjustments (placeholder — returns 0 until team stores rows)
-- ════════════════════════════════════════════════════════════════════════════

uplift_a1a3 AS (
    SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'upscaling_adjustment_tco2e', ''), '-')::numeric, 0)), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND project_option_id = :option_id
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'completeness' AND extra_fields->>'module' = 'a1_a3'
),
uplift_a4 AS (
    SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'upscaling_adjustment_tco2e', ''), '-')::numeric, 0)), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND project_option_id = :option_id
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'completeness' AND extra_fields->>'module' = 'a4'
),
uplift_a5 AS (
    SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'upscaling_adjustment_tco2e', ''), '-')::numeric, 0)), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND project_option_id = :option_id
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'completeness' AND extra_fields->>'module' = 'a5'
),
uplift_b1 AS (
    SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'upscaling_adjustment_tco2e', ''), '-')::numeric, 0)), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND project_option_id = :option_id
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'completeness' AND extra_fields->>'module' = 'b1'
),
uplift_b2_b5 AS (
    SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'upscaling_adjustment_tco2e', ''), '-')::numeric, 0)), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND project_option_id = :option_id
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'completeness' AND extra_fields->>'module' = 'b2_b5'
),
uplift_b6 AS (
    SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'upscaling_adjustment_tco2e', ''), '-')::numeric, 0)), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND project_option_id = :option_id
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'completeness' AND extra_fields->>'module' = 'b6'
),
uplift_b7 AS (
    SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'upscaling_adjustment_tco2e', ''), '-')::numeric, 0)), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND project_option_id = :option_id
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'completeness' AND extra_fields->>'module' = 'b7'
)

SELECT
    (SELECT val FROM er_a1a3)  + (SELECT val FROM uplift_a1a3)                                       AS a1_a3,
    (SELECT val FROM er_a4)    + (SELECT val FROM uplift_a4)                                          AS a4,
    (SELECT val FROM er_a5) + (SELECT val FROM a5_sat4p) + (SELECT val FROM a5_elec) + (SELECT val FROM uplift_a5) AS a5,
    (SELECT val FROM b1)       + (SELECT val FROM uplift_b1)                                          AS b1,
    (SELECT val FROM b2_b5)    + (SELECT val FROM uplift_b2_b5)                                       AS b2_b5,
    (SELECT val FROM b6_op)    + (SELECT val FROM b6_detailed) + (SELECT val FROM er_b6_elec) + (SELECT val FROM uplift_b6) AS b6,
    (SELECT val FROM b7)       + (SELECT val FROM uplift_b7)                                          AS b7,
    (SELECT val FROM b8)                                                                               AS b8,
    (SELECT val FROM offsets)                                                                          AS offsets
""")


# ─────────────────────────────────────────────────────────────────────────────
# SQL — resolve BUSINESS_CASE stage instance for the project
# ─────────────────────────────────────────────────────────────────────────────

_STAGE_INSTANCE_SQL = text("""
SELECT id
FROM project_stage_instances
WHERE project_id = :project_id
  AND stage = 'BUSINESS_CASE'
LIMIT 1
""")


# ─────────────────────────────────────────────────────────────────────────────
# SQL — project commencement year (used as carbon price year)
# ─────────────────────────────────────────────────────────────────────────────

_PROJECT_YEAR_SQL = text("""
SELECT EXTRACT(YEAR FROM commencement_of_operations)::int AS carbon_year
FROM project
WHERE id = :project_id
""")


# ─────────────────────────────────────────────────────────────────────────────
# SQL — project options for a stage instance, ordered by option_number
# ─────────────────────────────────────────────────────────────────────────────

_OPTIONS_SQL = text("""
SELECT id, label, option_number, is_default
FROM project_options
WHERE project_id        = :project_id
  AND stage_instance_id = :stage_instance_id
ORDER BY option_number
""")


# ─────────────────────────────────────────────────────────────────────────────
# SQL — carbon prices for the project's jurisdiction and commencement year
#
# Joins via project_dataset_revisions so we only get prices from dataset
# range code; ties broken by most-recently created dataset revision.
# Projects without a specific dataset revision linked will use the latest
# available carbon values for their jurisdiction and year.
# ─────────────────────────────────────────────────────────────────────────────

_CARBON_PRICE_SQL = text("""
SELECT DISTINCT ON (cv.range_code)
    cv.range_code,
    cvr.name              AS range_name,
    cv.value              AS carbon_price,
    COALESCE(cv.currency, '') AS currency
FROM carbon_values cv
JOIN carbon_value_ranges cvr
    ON cvr.code = cv.range_code
JOIN jurisdictions j
    ON j.id = cv.jurisdiction_id
JOIN dataset_revisions dr
    ON dr.id = cv.dataset_revision_id
WHERE j.name     = :jurisdiction
  AND cv.year    = :carbon_year
ORDER BY cv.range_code, dr.created_at DESC
""")


# ─────────────────────────────────────────────────────────────────────────────
# Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/summary",
    response_model=OptionsComparisonResponse,
    summary="Options comparison: total emissions and carbon value per project option",
)
async def get_options_comparison_summary(
    project_id:           UUID = Query(..., description="Project UUID"),
    elec_method:          str  = Query("location", description="Electricity accounting: 'location' or 'market'"),
    project_option_id:    Optional[UUID] = Query(None, description="Project option UUID (optional filter)"),
    submission_period_id: Optional[UUID] = Query(None, description="Submission period UUID (optional filter)"),
    db: AsyncSession = Depends(get_session),
) -> OptionsComparisonResponse:
    """
    Returns a three-section comparison across all project options for the
    BUSINESS_CASE stage:

    1. **totalEmissions** — total A1–B8 tCO₂e per option, with one row per
       carbon-price range (Low / Central / High).  The emissions value is the
       same in every row; the row structure exists to pair with Table 2.

    2. **totalCarbonValue** — total carbon cost per option per range:
       `carbon_value = total_a1_b8 × carbon_price_for_range`

    3. **chartData** — flat list of (option, total_a1_b8) for the bar chart.

    Carbon prices are looked up from the `carbon_values` table filtered by
    jurisdiction and the project's `commencement_of_operations` year.
    """
    if elec_method not in ("location", "market"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="elec_method must be 'location' or 'market'",
        )

    pid = str(project_id)

    # ── Resolve jurisdiction ─────────────────────────────────────────────────
    jurisdiction = await ProjectContextHelper.fetch_jurisdiction(db, project_id)

    # ── Resolve BUSINESS_CASE stage instance ────────────────────────────────
    si_result = await db.execute(_STAGE_INSTANCE_SQL, {"project_id": pid})
    si_row = si_result.mappings().fetchone()
    if si_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No BUSINESS_CASE stage instance found for this project",
        )
    stage_instance_id = str(si_row["id"])

    # ── Resolve carbon price year ────────────────────────────────────────────
    yr_result = await db.execute(_PROJECT_YEAR_SQL, {"project_id": pid})
    yr_row = yr_result.mappings().fetchone()
    carbon_year: int = (
        yr_row["carbon_year"]
        if yr_row and yr_row["carbon_year"] is not None
        else datetime.date.today().year
    )

    # ── Fetch project options ────────────────────────────────────────────────
    opts_result = await db.execute(
        _OPTIONS_SQL,
        {"project_id": pid, "stage_instance_id": stage_instance_id},
    )
    options = opts_result.mappings().fetchall()
    if not options:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No project options found for the BUSINESS_CASE stage",
        )

    if project_option_id:
        options = [o for o in options if str(o["id"]) == str(project_option_id)]
        if not options:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The specified project_option_id was not found for this project",
            )

    spid = str(submission_period_id) if submission_period_id else None

    # ── Fetch carbon prices (one per range code) ─────────────────────────────
    cp_result = await db.execute(
        _CARBON_PRICE_SQL,
        {"jurisdiction": jurisdiction, "carbon_year": carbon_year},
    )
    carbon_prices: Dict[str, dict] = {}
    for row in cp_result.mappings().fetchall():
        carbon_prices[row["range_code"]] = {
            "range_name":   row["range_name"],
            "carbon_price": Decimal(str(row["carbon_price"])) if row["carbon_price"] is not None else Decimal(0),
            "currency":     row["currency"] or "",
        }

    # ── Calculate total A1–B8 tCO₂e per option ──────────────────────────────
    def _dec(val) -> Decimal:
        if val is None:
            return Decimal(0)
        return Decimal(str(val))

    option_totals: Dict[str, Decimal] = {}
    for opt in options:
        params = {
            "project_id":           pid,
            "stage_instance_id":    stage_instance_id,
            "option_id":            str(opt["id"]),
            "elec_method":          elec_method,
            "jurisdiction":         jurisdiction,
            "submission_period_id": spid,
        }
        mod_result = await db.execute(_OPTION_MODULE_SQL, params)
        mod_row = mod_result.mappings().fetchone()

        total = Decimal(0)
        if mod_row:
            for _, _, col in _MODULE_META:
                # Sum only the A1–B8 modules; exclude offsets and stored carbon
                if col is not None and col not in ("offsets", "stored_carbon"):
                    total += _dec(mod_row[col])
        option_totals[str(opt["id"])] = total

    # ── Map DB range codes to frontend keys: low→min, central→medium, high→max
    _KEY = {"low": "min", "central": "medium", "high": "max"}

    # Get currency label from any available range (all rows share the same currency)
    currency = next((v["currency"] for v in carbon_prices.values()), "")

    # ── Build one ProjectOptionData per option ────────────────────────────────
    project_option_list: List[ProjectOptionData] = []
    for opt in options:
        total = option_totals[str(opt["id"])]

        emissions_vals = {
            _KEY[r]: total
            for r in ("low", "central", "high")
            if r in carbon_prices
        }
        carbon_vals = {
            _KEY[r]: total * carbon_prices[r]["carbon_price"]
            for r in ("low", "central", "high")
            if r in carbon_prices
        }

        project_option_list.append(
            ProjectOptionData(
                label=opt["label"],
                emissions=EmissionsRange(**emissions_vals),
                carbonValue=CarbonValueRange(**carbon_vals),
            )
        )

    return OptionsComparisonResponse(
        unit=UnitInfo(emissions="tCO2e", carbonValue=currency),
        projectOptions=project_option_list,
    )

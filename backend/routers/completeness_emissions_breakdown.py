"""
routers/completeness_emissions_breakdown.py

Completeness feature API — base module emissions and upscaling calculations.

Isolated copy of dashboard emissions breakdown logic (without completeness uplifts
applied) so future dashboard changes do not break the Completeness data-entry tab.

Returns:
  modules          — emissions totals per lifecycle module
  sourceCategories — emissions totals per source category
  summaryIndicators— headline KPI (total gross emissions)

─────────────────────────────────────────────────────────────────────────────
Module allocation rules (from Emissions breakdown.csv)
─────────────────────────────────────────────────────────────────────────────

A1-A3  (Raw material supply, Transport, Manufacturing)
  - asset                               : product_stage_a1a3      [Grade 1 — A1-A3 stage portion]
  - component (Grade 2)                 : product_stage_a1_a3_tco2e from extra_fields (primary);
                                          falls back to "Product Stage (A1-3) (tCO2e/UoM)" × qty
                                          via v_grade2_component_level, then total_emissions_tco2e
  - bcDetailedLevel / constructionG3 /
    recurringG3  where cat='Materials'  : product_stage_a1_a3_tco2e from extra_fields
  - concreteRegSimplified / Detailed    : total_emissions_tco2e
  - shortcutIsMaterials (non-maint.)    : extra_fields->>'actual_case'
  - shortcutSat4p where source =
    'Construction materials'            : actual_scope3 + actual_scope4

A4  (Transport to site)
  - asset                               : transport_a4            [Grade 1 — A4 stage portion]
  - component (Grade 2)                 : transport_stage_a4_tco2e from extra_fields (primary);
                                          falls back to "Transport Stage (A4) (tCO2e/UoM)" × qty
  - bcDetailedLevel / constructionG3 /
    recurringG3  where cat='Materials'  : transport_stage_a4_tco2e from extra_fields
  - shortcutSat4p where source =
    'Transport (construction materials)': actual_scope3 + actual_scope4

A5  (Construction installation process)
  - asset                               : construction_a5         [Grade 1 — A5 stage portion]
  - component (Grade 2)                 : construction_stage_a5_tco2e from extra_fields (primary);
                                          falls back to "Construction Stage (A5) (tCO2e/UoM)" × qty
  - bcDetailedLevel / constructionG3 /
    recurringG3  non-Materials & non-Offset: construction_stage_a5_tco2e (fallback: total_tco2e)
  - electricity                         : location_based_tco2e / market_based_tco2e
  - shortcutSat4p other sources         : actual_scope3 + actual_scope4

B1  (Use)
  - useB1G2, useB1G3                    : total_emissions_tco2e

B2-B5  (Maintenance, Repair, Replacement, Refurbishment)
  - componentRepl, refurbishment,
    replDetailed                        : total_emissions_tco2e

B6  (Operational energy — non-Water)
  - opEnergy                            : location/market_based_total_tco2e
  - opEnergyDetailed where cat≠'Water'  : total_emissions_tco2e
  - opEnergyElectricity                 : location/market_based_tco2e

B7  (Water)
  - opEnergyDetailed where cat='Water'  : total_emissions_tco2e

B8  (Users)
  - roadUsers, railUsers                : total_emissions_tco2e  (small projects)
  - largeRoadUsers, largeRoadParams,
    largeRailUsers                      : total_emissions_tco2e  (large projects)

Offsets  (NOT included in A1–B8 totals; returned as negative value)
  - bcDetailedLevel / constructionG3 /
    recurringG3 / replDetailed /
    opEnergyDetailed  where cat='Offset': total_emissions_tco2e

Stored carbon  (returned as negative value)
  - component (Grade 2)                 : "Carbon Storage (tCO2e/UoM)" × qty via
                                          v_grade2_component_level join
  - bcDetailedLevel (Grade 3/4)         : "Carbon Storage (tCO2e/UoM)" × qty via
                                          v_grade34_detailed_level join (5-key incl. Sub-Category)

─────────────────────────────────────────────────────────────────────────────
Query params
─────────────────────────────────────────────────────────────────────────────
  project_id        UUID  required
  stage_instance_id UUID  required
  elec_method       str   optional — 'location' (default) | 'market'
  jurisdiction      str   resolved automatically from project → organisation → jurisdiction
                            (falls back to 'Australia' if not configured)

─────────────────────────────────────────────────────────────────────────────
Completeness upscaling adjustment
─────────────────────────────────────────────────────────────────────────────
  Uplift rows stored in activity_data with ui_table_key = 'completeness':
    extra_fields->>'module'                    'a1_a3' | 'a4' | 'a5' | 'b1' | 'b2_b5' | 'b6' | 'b7'
    extra_fields->>'upscaling_adjustment_tco2e' additive tCO2e adjustment
  POST /calculate computes upscaling from base module values (this router's SQL)
  and persists rows; dashboard applies stored uplifts via TIER 4 in its own router.
  Applies to: A1-A3, A4, A5, B1, B2-B5, B6, B7 (NOT B8, Offsets, Stored carbon).
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import Field
from services._calc_utils import DashboardBase
from services.project_context_helper import ProjectContextHelper
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from routers.dashboard_carbon_storage import _DETAIL_SQL as _CARBON_STORAGE_DETAIL_SQL

router = APIRouter(
    prefix="/api/dashboard/completeness-emissions-breakdown",
    tags=["Dashboard - Completeness Emissions Breakdown"],
)

COMPLETENESS_MODULE_DEFS = [
    ("a1_a3", "A1-A3", "a1_a3"),
    ("a4", "A4", "a4"),
    ("a5", "A5", "a5"),
    ("b1", "B1", "b1"),
    ("b2_b5", "B2-B5", "b2_b5"),
    ("b6", "B6", "b6"),
    ("b7", "B7", "b7"),
]

COMPLETENESS_MIN_PCT = Decimal("80")
COMPLETENESS_MAX_PCT = Decimal("100")


# ─────────────────────────────────────────────────────────────────────────────
# Response models
# ─────────────────────────────────────────────────────────────────────────────

class ModuleRow(DashboardBase):
    """Emissions total for one lifecycle module."""
    code: str       # e.g. "A1", "A4", "A5", "B1", "B2", "B6", "B7", "B8", "Offsets", "Stored carbon"
    label: str      # Display label shown in the table / chart
    value: Decimal  # tCO2e (negative for Offsets and Stored carbon)


class SourceCategoryRow(DashboardBase):
    """Emissions total for one source category."""
    category: str   # e.g. "Materials", "Electricity", "Fuels", "Gases", "Waste"
    value: Decimal  # tCO2e


class SummaryIndicator(DashboardBase):
    value: Decimal
    unit: str


class SummaryIndicators(DashboardBase):
    primaryIndicator: Optional[SummaryIndicator] = None    # Total gross A1–B8 emissions
    secondaryIndicator: Optional[SummaryIndicator] = None  # Reserved for future intensity metric


class ModuleCompletenessInput(DashboardBase):
    module: str
    completeness_pct: Decimal = Field(..., ge=80, le=100)


class CalculateRequest(DashboardBase):
    project_id: UUID
    stage_instance_id: UUID
    project_option_id: Optional[UUID] = None
    submission_period_id: Optional[UUID] = None
    elec_method: str = "location"
    modules: List[ModuleCompletenessInput]


class ModuleCalculationResult(DashboardBase):
    module: str
    label: str
    completeness_pct: Decimal
    base_emissions_tco2e: Decimal
    upscaling_adjustment_tco2e: Decimal


class CalculateResponse(DashboardBase):
    modules: List[ModuleCalculationResult]
    total_uplift_tco2e: Decimal


class EmissionsBreakdownResponse(DashboardBase):
    """
    Full response for the Emissions Breakdown dashboard tab.

    modules          → drives the 'Emissions breakdown by module' table and doughnut chart
    sourceCategories → drives the 'Emissions breakdown by source category' table / treemap
    summaryIndicators→ headline KPIs (total emissions, optional intensity)
    """
    modules: List[ModuleRow]
    sourceCategories: List[SourceCategoryRow]
    summaryIndicators: Optional[SummaryIndicators] = None


# ─────────────────────────────────────────────────────────────────────────────
# SQL — module breakdown
# Returns one row with a column per lifecycle module.
# ─────────────────────────────────────────────────────────────────────────────

_BASE_MODULE_SQL = text("""
WITH

-- ════════════════════════════════════════════════════════════════════════════
-- TIER 1 — emissions_results JOIN (canonical per-module tCO2e)
--
-- For each activity_data row the developer stores one emissions_results row
-- per value_key.  Current codes in value_key include:
--   A1-A3  A4  A5  B2-5  C2  C3-4
-- A5 note: electricity rows are excluded from er_a5 and handled separately
-- via a5_elec (reads extra_fields location/market totals directly).
-- SAT4P shortcut A5 rows are not in emissions_results; handled by a5_sat4p.
-- Developer will add codes for B1, B6 (non-elec), B7, B8, Offsets, Stored carbon.
-- Once added, replace the corresponding TIER 2 CTE with an emissions_results JOIN.
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
      AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
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
      AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
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
      AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
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
              AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
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
      AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
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
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
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
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
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
    -- NOTE: SAT4P maintenance sources ('Maintenance processes / equipment',
    --       'Transport (maintenance materials)') should also sum to B2-B5;
    --       add a b2_b5_sat4p CTE if those rows are not written to emissions_results.
    SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)), 0) AS val
    FROM activity_data
    WHERE project_id                = :project_id
      AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key IN ('componentRepl', 'refurbishment', 'replDetailed')
      AND NOT (ui_table_key = 'replDetailed' AND COALESCE(extra_fields->>'emissions_category', '') = 'Offset')
),

er_b6_elec AS (
    -- Operational electricity (ui_table_key='opEnergyElectricity').
    -- Uses location_based_tco2e / market_based_tco2e from extra_fields.
    -- These are the Scope 2+3 totals (sum of scope2 + scope3 columns).
    SELECT COALESCE(SUM(
        CASE WHEN :elec_method = 'market'
             THEN COALESCE(NULLIF(NULLIF(extra_fields->>'market_based_tco2e',   ''), '-')::numeric, 0)
             ELSE COALESCE(NULLIF(NULLIF(extra_fields->>'location_based_tco2e', ''), '-')::numeric, 0)
        END
    ), 0) AS val
    FROM activity_data
    WHERE project_id                = :project_id
      AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'opEnergyElectricity'
),

-- ════════════════════════════════════════════════════════════════════════════
-- TIER 2 — modules not yet in lifecycle_modules (extra_fields fallback)
-- Developer will add lifecycle codes for B1, B6 (non-elec), B7, B8, Offsets.
-- Once each code is added, replace that CTE with an emissions_results JOIN.
-- ════════════════════════════════════════════════════════════════════════════

b1 AS (
    SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key IN ('useB1G2', 'useB1G3')
),

b6_op AS (
    -- Component Level (Grade 2): use opEnergy method-specific totals.
    -- Mirrors er_b6_elec behavior: market branch, otherwise location branch.
    SELECT COALESCE(SUM(
        CASE WHEN :elec_method = 'market'
             THEN COALESCE(NULLIF(NULLIF(extra_fields->>'market_based_total_tco2e', ''), '-')::numeric, 0)
             ELSE COALESCE(NULLIF(NULLIF(extra_fields->>'location_based_total_tco2e', ''), '-')::numeric, 0)
        END
    ), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'opEnergy'
),

b6_detailed AS (
    -- opEnergyDetailed non-Water, non-Offset rows (Offset rows are captured in the offsets CTE)
    SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'opEnergyDetailed'
      AND COALESCE(extra_fields->>'emissions_category', '') NOT IN ('Water', 'Offset')
),

b7 AS (
    SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'opEnergyDetailed'
      AND extra_fields->>'emissions_category' = 'Water'
),

b8_road AS (
    -- Small project road users: relativeUserEmissions
    SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'relativeUserEmissions', ''), '-')::numeric, 0)), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'roadUsers'
),

b8_rail AS (
    -- Rail users (small and large): emissions_total_ref_period_tco2e
    SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'emissions_total_ref_period_tco2e', ''), '-')::numeric, 0)), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
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
          AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
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
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key IN (
          'bcDetailedLevel', 'constructionG3', 'recurringG3',
          'replDetailed', 'opEnergyDetailed'
      )
      AND extra_fields->>'emissions_category' = 'Offset'
)

SELECT
    (SELECT val FROM er_a1a3) AS a1_a3,
    (SELECT val FROM er_a4) AS a4,
    (SELECT val FROM er_a5) + (SELECT val FROM a5_sat4p) + (SELECT val FROM a5_elec) AS a5,
    (SELECT val FROM b1) AS b1,
    (SELECT val FROM b2_b5) AS b2_b5,
    (SELECT val FROM b6_op) + (SELECT val FROM b6_detailed) + (SELECT val FROM er_b6_elec) AS b6,
    (SELECT val FROM b7) AS b7,
    (SELECT val FROM b8) AS b8,
    (SELECT val FROM offsets) AS offsets,
    0::numeric AS stored_carbon
""")


# ─────────────────────────────────────────────────────────────────────────────
# SQL — source category breakdown
# Returns one row per emissions_category with total tCO2e.
# Each data source normalises its value to a category and a numeric val so
# UNION ALL can be summed cleanly without special-casing upstream.
# ─────────────────────────────────────────────────────────────────────────────

_SOURCE_SQL = text("""
SELECT
    category,
    SUM(val) AS emissions_tco2e
FROM (

    -- Grade 3/4 detailed rows (use stored total_emissions_tco2e; category from extra_fields)
    SELECT
        COALESCE(NULLIF(TRIM(extra_fields->>'emissions_category'), ''), 'Other') AS category,
        COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)  AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key IN (
          'bcDetailedLevel', 'constructionG3', 'recurringG3',
          'useB1G3',
          'replDetailed', 'opEnergyDetailed'
      )
      AND COALESCE(extra_fields->>'emissions_category', '') != 'Offset'

    UNION ALL

    -- Grade 2 component rows (category from extra_fields)
    SELECT
        COALESCE(NULLIF(TRIM(extra_fields->>'emissions_category'), ''), 'Other') AS category,
        COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)  AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key IN ('component', 'componentRepl', 'useB1G2')

    UNION ALL

    -- Grade 1 asset rows — classified as 'Materials'
    SELECT
        'Materials'::text AS category,
        COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'asset'

    UNION ALL

    -- Concrete registers — classified as 'Materials'
    SELECT
        'Materials'::text AS category,
        COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key IN ('concreteRegSimplified', 'concreteRegDetailed')

    UNION ALL

    -- Refurbishment rows (category from extra_fields)
    SELECT
        COALESCE(NULLIF(TRIM(extra_fields->>'emissions_category'), ''), 'Other') AS category,
        COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'refurbishment'

    UNION ALL

    -- Construction electricity — classified as 'Electricity'
    SELECT
        'Electricity'::text AS category,
        CASE WHEN :elec_method = 'market'
             THEN COALESCE(NULLIF(NULLIF(extra_fields->>'market_based_tco2e', ''), '-')::numeric, 0)
             ELSE COALESCE(NULLIF(NULLIF(extra_fields->>'location_based_tco2e', ''), '-')::numeric, 0)
        END AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'electricity'

    UNION ALL

    -- Operational electricity — classified as 'Electricity'
    SELECT
        'Electricity'::text AS category,
        CASE WHEN :elec_method = 'market'
             THEN COALESCE(NULLIF(NULLIF(extra_fields->>'market_based_tco2e', ''), '-')::numeric, 0)
             ELSE COALESCE(NULLIF(NULLIF(extra_fields->>'location_based_tco2e', ''), '-')::numeric, 0)
        END AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'opEnergyElectricity'

    UNION ALL

    -- opEnergy (Grade 2 operational) — classified as 'Electricity'
    SELECT
        'Electricity'::text AS category,
        CASE WHEN :elec_method = 'market'
             THEN COALESCE(NULLIF(NULLIF(extra_fields->>'market_based_total_tco2e', ''), '-')::numeric, 0)
             ELSE COALESCE(NULLIF(NULLIF(extra_fields->>'location_based_total_tco2e', ''), '-')::numeric, 0)
        END AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'opEnergy'

    UNION ALL

    -- Shortcut IS Materials — classified as 'Materials'
    SELECT
        'Materials'::text AS category,
        COALESCE(NULLIF(NULLIF(extra_fields->>'actual_case', ''), '-')::numeric, 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'shortcutIsMaterials'
      AND (extra_fields->>'row_type' IS DISTINCT FROM 'maintenance')

    UNION ALL

    -- Shortcut SAT4P — source-based category assignment
    SELECT
        CASE extra_fields->>'source'
            WHEN 'Construction materials'             THEN 'Materials'
            WHEN 'Transport (construction materials)' THEN 'Fuels'
            ELSE                                           'Fuels'
        END AS category,
        COALESCE(NULLIF(NULLIF(extra_fields->>'actual_scope3', ''), '-')::numeric, 0) +
        COALESCE(NULLIF(NULLIF(extra_fields->>'actual_scope4', ''), '-')::numeric, 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'shortcutSat4p'

) all_rows
GROUP BY category
HAVING SUM(val) > 0
ORDER BY SUM(val) DESC
""")


# ─────────────────────────────────────────────────────────────────────────────
# Module metadata: display labels and ordering
# ─────────────────────────────────────────────────────────────────────────────

_MODULE_META = [
    # (code, label, sql_column)
    # A1-A3 combined — reported under code "A1"; A2 and A3 are returned as zero
    # so the frontend can display all three slots if needed.
    ("A1",            "A1-A3 Raw material supply, transport & manufacturing", "a1_a3"),
    ("A2",            "A2 (included in A1-A3)",                              None),
    ("A3",            "A3 (included in A1-A3)",                              None),
    ("A4",            "A4 Transport to site",                                "a4"),
    ("A5",            "A5 Construction installation process",                "a5"),
    ("B1",            "B1 Use",                                              "b1"),
    # B2-B5 combined — reported under code "B2"
    ("B2",            "B2-B5 Maintenance, repair, replacement & refurbishment", "b2_b5"),
    ("B3",            "B3 (included in B2-B5)",                              None),
    ("B4",            "B4 (included in B2-B5)",                              None),
    ("B5",            "B5 (included in B2-B5)",                              None),
    ("B6",            "B6 Operational energy use",                           "b6"),
    ("B7",            "B7 Operational water use",                            "b7"),
    ("B8",            "B8 Users",                                            "b8"),
    ("Offsets",       "Offsets",                                             "offsets"),
    ("Stored carbon", "Stored carbon",                                       "stored_carbon"),
]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _dec(val) -> Decimal:
    if val is None:
        return Decimal(0)
    return Decimal(str(val))


def _round_emissions(val: Decimal) -> Decimal:
    return val.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


async def _fetch_base_module_row(db: AsyncSession, params: dict) -> dict:
    mod_result = await db.execute(_BASE_MODULE_SQL, params)
    _raw = mod_result.mappings().fetchone()
    if _raw is None:
        mod_row: dict = {col: Decimal(0) for col in [
            "a1_a3", "a4", "a5", "b1", "b2_b5", "b6", "b7", "b8",
            "offsets", "stored_carbon",
        ]}
    else:
        mod_row = dict(_raw)

    cs_result = await db.execute(_CARBON_STORAGE_DETAIL_SQL, params)
    mod_row["stored_carbon"] = sum(
        (_dec(r["carbon_storage_tco2e"]) for r in cs_result.mappings().all()),
        Decimal(0),
    )
    return mod_row


def _compute_uplift(base_emissions: Decimal, completeness_pct: Decimal) -> Decimal:
    pct_decimal = completeness_pct / Decimal(100)
    if pct_decimal <= 0:
        return Decimal(0)
    uplift_factor = (Decimal(1) / pct_decimal) - Decimal(1)
    return _round_emissions(base_emissions * uplift_factor)


# ─────────────────────────────────────────────────────────────────────────────
# Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/summary",
    response_model=EmissionsBreakdownResponse,
    summary="Base emissions breakdown by module (pre-completeness uplift)",
)
async def get_completeness_base_summary(
    project_id:           UUID = Query(..., description="Project UUID"),
    stage_instance_id:    UUID = Query(..., description="Project stage instance UUID"),
    elec_method:          str  = Query("location", description="Electricity accounting: 'location' or 'market'"),
    project_option_id:    Optional[UUID] = Query(None, description="Project option UUID (optional filter)"),
    submission_period_id: Optional[UUID] = Query(None, description="Submission period UUID (optional filter)"),
    db: AsyncSession = Depends(get_session),
) -> EmissionsBreakdownResponse:
    """
    Returns emissions broken down by lifecycle module (A1-A3 … B8, Offsets, Stored carbon)
    and by source category (Materials, Electricity, Fuels, etc.) for the specified
    project stage instance.

    Electricity emissions are reported using the `elec_method` parameter:
      - 'location' (default): location-based accounting
      - 'market': market-based accounting (reflects renewable energy purchases / GreenPower)

    The jurisdiction is resolved automatically from the project's proponent organisation.
    Grade 2 component-level emissions are split into A1-A3 / A4 / A5 by joining to
    v_grade2_component_level using the resolved jurisdiction.

    Grade 3/4 Materials rows are split into A1-A3 (scope3_ef × qty) and A4 (residual)
    by joining to v_grade34_detailed_level.
    """
    if elec_method not in ("location", "market"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="elec_method must be 'location' or 'market'",
        )

    # Resolve jurisdiction from project → organisation → jurisdiction
    jurisdiction = await ProjectContextHelper.fetch_jurisdiction(db, project_id)

    params = {
        "project_id":           str(project_id),
        "stage_instance_id":    str(stage_instance_id),
        "elec_method":          elec_method,
        "jurisdiction":         jurisdiction,
        "project_option_id":    str(project_option_id) if project_option_id else None,
        "submission_period_id": str(submission_period_id) if submission_period_id else None,
    }

    # ── Module totals ────────────────────────────────────────────────────────
    mod_row = await _fetch_base_module_row(db, params)

    modules: List[ModuleRow] = []
    for code, label, col in _MODULE_META:
        if col is None:
            # Placeholder code (e.g. A2, A3, B3-B5) — always zero, kept for frontend ordering
            modules.append(ModuleRow(code=code, label=label, value=Decimal(0)))
        else:
            modules.append(ModuleRow(code=code, label=label, value=_dec(mod_row[col])))

    # ── Source categories ────────────────────────────────────────────────────
    src_result = await db.execute(_SOURCE_SQL, params)
    src_rows   = src_result.mappings().fetchall()

    source_categories: List[SourceCategoryRow] = [
        SourceCategoryRow(
            category=r["category"],
            value=_dec(r["emissions_tco2e"]),
        )
        for r in src_rows
    ]

    # ── Summary indicators ───────────────────────────────────────────────────
    # Primary indicator: total gross A1-B8 emissions (excludes Offsets and Stored carbon)
    gross_total = sum(
        _dec(mod_row[col])
        for _, _, col in _MODULE_META
        if col is not None and col not in ("offsets", "stored_carbon")
    )
    summary_indicators = SummaryIndicators(
        primaryIndicator=SummaryIndicator(value=gross_total, unit="tCO\u2082e"),
    )

    return EmissionsBreakdownResponse(
        modules=modules,
        sourceCategories=source_categories,
        summaryIndicators=summary_indicators,
    )


@router.post(
    "/calculate",
    response_model=CalculateResponse,
    summary="Calculate completeness upscaling adjustments (tCO2e) per module",
)
async def calculate_completeness_uplift(
    payload: CalculateRequest = Body(...),
    db: AsyncSession = Depends(get_session),
) -> CalculateResponse:
    if payload.elec_method not in ("location", "market"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="elec_method must be 'location' or 'market'",
        )

    allowed_modules = {m[0] for m in COMPLETENESS_MODULE_DEFS}
    for item in payload.modules:
        if item.module not in allowed_modules:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid module '{item.module}'. Allowed: {sorted(allowed_modules)}",
            )
        if item.completeness_pct < COMPLETENESS_MIN_PCT or item.completeness_pct > COMPLETENESS_MAX_PCT:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Allowed range is between 80 to 100",
            )

    jurisdiction = await ProjectContextHelper.fetch_jurisdiction(db, payload.project_id)
    params = {
        "project_id": str(payload.project_id),
        "stage_instance_id": str(payload.stage_instance_id),
        "elec_method": payload.elec_method,
        "jurisdiction": jurisdiction,
        "project_option_id": str(payload.project_option_id) if payload.project_option_id else None,
        "submission_period_id": str(payload.submission_period_id) if payload.submission_period_id else None,
    }

    mod_row = await _fetch_base_module_row(db, params)
    pct_by_module = {item.module: item.completeness_pct for item in payload.modules}

    results: List[ModuleCalculationResult] = []
    total_uplift = Decimal(0)

    for module_key, label, sql_col in COMPLETENESS_MODULE_DEFS:
        completeness_pct = pct_by_module.get(module_key, COMPLETENESS_MIN_PCT)
        base = _dec(mod_row.get(sql_col))
        uplift = _compute_uplift(base, completeness_pct)
        total_uplift += uplift
        results.append(
            ModuleCalculationResult(
                module=module_key,
                label=label,
                completeness_pct=completeness_pct,
                base_emissions_tco2e=_round_emissions(base),
                upscaling_adjustment_tco2e=uplift,
            )
        )

    return CalculateResponse(
        modules=results,
        total_uplift_tco2e=_round_emissions(total_uplift),
    )

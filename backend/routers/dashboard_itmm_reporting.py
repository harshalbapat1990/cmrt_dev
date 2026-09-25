"""
routers/dashboard_itmm_reporting.py

Dashboard Results API — ITMM Reporting: LCA Module Breakdown

Returns a per-lifecycle-module comparison of Baseline vs Actual emissions,
with absolute and per-declared-unit columns, difference, and reduction
percentages.  Mirrors the structure of the ITMM Reporting table in the
Carbon Management & Reporting Tool.

─────────────────────────────────────────────────────────────────────────────
Table rows (in order)
─────────────────────────────────────────────────────────────────────────────
  a1_a3_excl_biogenic   — Product stage (A1-A3) - excl biogenic carbon
  a1_a3_biogenic        — Product stage (A1-A3) - sequestered biogenic carbon
  a4                    — Transport to site (A4)
  a5_construction       — Construction (A5)
  a5_land_use_change    — Land use change (A5)
  total_upfront         — Total upfront carbon (A1-A5) - excl biogenic carbon [subtotal]
  b1_1                  — Use - material emissions and removals (B1.1)
  b2_b5                 — Maintenance (B2), Repair (B3), Refurbishment and replacement (B4-B5)
  total_in_use_embodied — Total in-use embodied carbon (B1.1, B2-B5) [subtotal]
  b1_2                  — Use - operational processes (B1.2) [placeholder = 0]
  b6                    — Operational energy (B6)
  b7                    — Operational water (B7)
  total_in_use_operational — Total in-use operational carbon (B1.2, B6-B7) [subtotal]
  b8                    — Users (B8)

─────────────────────────────────────────────────────────────────────────────
Baseline vs Actual calculation
─────────────────────────────────────────────────────────────────────────────
  Actual  = identical to the Emissions Breakdown screen values per module
  Baseline = Actual + emissions from all Mitigations data-entry tables
             (avoidance + net substitution), allocated by module, PLUS
             the difference between Base Case and Actual Case for shortcut
             tables (shortcutIsMaterials, shortcutSat4p).

─────────────────────────────────────────────────────────────────────────────
Biogenic (stored carbon)
─────────────────────────────────────────────────────────────────────────────
  Both Baseline and Actual show the same stored_carbon value (mitigations
  do not change biogenic carbon amounts).

─────────────────────────────────────────────────────────────────────────────
A5 split
─────────────────────────────────────────────────────────────────────────────
  Construction A5 = total A5 emissions EXCLUDING bcDetailedLevel rows where
                    emissions_category = 'Vegetation'
  Land use change A5 = bcDetailedLevel rows where
                    emissions_category = 'Vegetation'

─────────────────────────────────────────────────────────────────────────────
Query params
─────────────────────────────────────────────────────────────────────────────
  project_id        UUID  required
  stage_instance_id UUID  required
  elec_method       str   optional — 'location' (default) | 'market'
  project_option_id UUID  optional — filter to a specific project option
  submission_period_id UUID optional — filter to a specific submission period
"""

from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from services._calc_utils import DashboardBase
from services.project_context_helper import ProjectContextHelper
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from routers.dashboard_carbon_storage import _DETAIL_SQL as _CARBON_STORAGE_DETAIL_SQL

router = APIRouter(
    prefix="/api/dashboard/itmm-reporting",
    tags=["Dashboard - ITMM Reporting"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Response models
# ─────────────────────────────────────────────────────────────────────────────

class ITMMModuleRow(DashboardBase):
    """One row in the ITMM Reporting LCA Module Breakdown table."""
    module_code: str
    module_label: str
    is_subtotal: bool = False
    baseline_absolute: Optional[Decimal] = None
    baseline_per_unit: Optional[Decimal] = None
    actual_absolute: Optional[Decimal] = None
    actual_per_unit: Optional[Decimal] = None
    difference_absolute: Optional[Decimal] = None   # baseline - actual
    difference_per_unit: Optional[Decimal] = None
    reduction_pct_absolute: Optional[Decimal] = None  # difference / baseline * 100
    reduction_pct_per_unit: Optional[Decimal] = None


class ITMMReportingResponse(DashboardBase):
    """Full response for the ITMM Reporting LCA Module Breakdown tab."""
    declared_unit_value: Optional[Decimal] = None
    declared_unit_type: Optional[str] = None
    rows: List[ITMMModuleRow]


# ─────────────────────────────────────────────────────────────────────────────
# SQL
# Returns one row with per-module Actual and Baseline values.
#
# Structure:
#   TIER 1 — emissions_results JOIN (canonical per-module tCO2e)
#   TIER 2 — extra_fields fallback (B1, B6 non-elec, B7, B8)
#   TIER 3 — stored carbon via view joins
#   TIER 4 — completeness upscaling (placeholder, returns 0)
#   MITIGATION — per-module mitigation contributions that inflate Baseline
#   SHORTCUT DELTAS — base_case minus actual_case from shortcut tables
# ─────────────────────────────────────────────────────────────────────────────

_ITMM_SQL = text("""
WITH

-- ════════════════════════════════════════════════════════════════════════════
-- TIER 1 — emissions_results JOIN
-- ════════════════════════════════════════════════════════════════════════════

er_a1a3 AS (
    SELECT COALESCE(SUM(er.value), 0) AS val
    FROM activity_data ad
    JOIN emissions_results er ON er.activity_data_id = ad.id
        AND er.value_key = 'A1-A3'
    WHERE ad.project_id                = :project_id
      AND ad.project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
),

er_a4 AS (
    SELECT COALESCE(SUM(er.value), 0) AS val
    FROM activity_data ad
    JOIN emissions_results er ON er.activity_data_id = ad.id
        AND er.value_key = 'A4'
    WHERE ad.project_id                = :project_id
      AND ad.project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
),

er_a5 AS (
    -- All A5 rows except electricity (electricity handled separately in er_a5_elec)
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

er_a5_vegetation AS (
    -- Land use change: bcDetailedLevel rows where emissions_category = 'Vegetation' with A5 code
    SELECT COALESCE(SUM(er.value), 0) AS val
    FROM activity_data ad
    JOIN emissions_results er ON er.activity_data_id = ad.id
        AND er.value_key = 'A5'
    WHERE ad.project_id                = :project_id
      AND ad.project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND ad.ui_table_key = 'bcDetailedLevel'
      AND ad.extra_fields->>'emissions_category' = 'Vegetation'
),

er_a5_elec AS (
    -- Construction electricity: location_based or market_based tco2e from extra_fields
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

-- B2-B5: read total_emissions_tco2e from extra_fields for componentRepl/refurbishment/replDetailed.
-- replDetailed Offset rows excluded (they belong to the offsetting category, not B2-B5).
b2_b5 AS (
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
    -- Operational electricity: location_based or market_based tco2e from extra_fields
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
-- TIER 2 — extra_fields fallback (B1, B6 non-elec, B7, B8)
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
    -- opEnergy: use operational total based on elec_method.
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
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'opEnergy'
),

b6_detailed AS (
    -- opEnergyDetailed non-Water, non-Offset rows (Offset rows are captured in the offsets section)
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
    -- Road user emissions: relativeUserEmissions field
    SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'relativeUserEmissions', ''), '-')::numeric, 0)), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'roadUsers'
),

b8_rail AS (
    -- Rail user emissions: emissions_total_ref_period_tco2e field
    SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'emissions_total_ref_period_tco2e', ''), '-')::numeric, 0)), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'railUsers'
),

b8_large_road AS (
    -- Large road user emissions: final_user_emissions_tco2e from largeRoadParams.
    -- Rows repeat per modelled year per parameter combo; deduplicate by taking MAX per combo.
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

-- ════════════════════════════════════════════════════════════════════════════
-- TIER 3 — stored carbon (biogenic) is computed in Python by executing
--           _CARBON_STORAGE_DETAIL_SQL and summing carbon_storage_tco2e.
--           EF values in the views are already negative (sequestration);
--           no CTE needed here.
-- ════════════════════════════════════════════════════════════════════════════

-- ════════════════════════════════════════════════════════════════════════════
-- TIER 4 — completeness upscaling adjustments (placeholder — returns 0)
-- ════════════════════════════════════════════════════════════════════════════

uplift_a1a3 AS (
    SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'upscaling_adjustment_tco2e', ''), '-')::numeric, 0)), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'completeness' AND extra_fields->>'module' = 'a1_a3'
),
uplift_a4 AS (
    SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'upscaling_adjustment_tco2e', ''), '-')::numeric, 0)), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'completeness' AND extra_fields->>'module' = 'a4'
),
uplift_a5 AS (
    SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'upscaling_adjustment_tco2e', ''), '-')::numeric, 0)), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'completeness' AND extra_fields->>'module' = 'a5'
),
uplift_b1 AS (
    SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'upscaling_adjustment_tco2e', ''), '-')::numeric, 0)), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'completeness' AND extra_fields->>'module' = 'b1'
),
uplift_b2_b5 AS (
    SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'upscaling_adjustment_tco2e', ''), '-')::numeric, 0)), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'completeness' AND extra_fields->>'module' = 'b2_b5'
),
uplift_b6 AS (
    SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'upscaling_adjustment_tco2e', ''), '-')::numeric, 0)), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'completeness' AND extra_fields->>'module' = 'b6'
),
uplift_b7 AS (
    SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'upscaling_adjustment_tco2e', ''), '-')::numeric, 0)), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'completeness' AND extra_fields->>'module' = 'b7'
),

-- ════════════════════════════════════════════════════════════════════════════
-- MITIGATION CONTRIBUTIONS — per-module baseline additions
--
-- Baseline rule (confirmed by James, matches GHG Scopes dashboard):
--   Baseline = Actual + avoidance/reduction rows + substitution-ADOPTED rows
--   Substitution-REPLACED rows are EXCLUDED from baseline.
--
--   Example:  Regular(Actual)=10, Reduction=3, Replaced=4, Adopted=1
--             Baseline = 10 + 3 + 1 = 14   (NOT 10 + 3 + (4-1) = 16)
--
-- Allocation of each source table to lifecycle module mirrors the same
-- rules as the Emissions Breakdown regular data entry tables.
-- ════════════════════════════════════════════════════════════════════════════

-- ── A1-A3 mitigation ────────────────────────────────────────────────────────
-- Sources: component, bcDetailedLevel (Materials), constructionG3 (Materials),
--          concreteRegSimplified, concreteRegDetailed, asset
-- Field: product_stage_a1_a3_tco2e for component/bcDetailedLevel/constructionG3;
--        total_emissions_tco2e for concrete registers and asset
-- Includes: avoidance rows (-mitigation) + substitution-adopted rows (-mitigation-subst-adopted)
-- Excludes: substitution-replaced rows (-mitigation-subst-replaced)
mit_a1a3 AS (
    -- component/bcDetailedLevel/constructionG3 (Materials or component): product_stage_a1_a3_tco2e
    SELECT COALESCE(SUM(
        COALESCE(NULLIF(NULLIF(extra_fields->>'product_stage_a1_a3_tco2e', ''), '-')::numeric, 0)
    ), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key IN (
          'component-mitigation', 'component-mitigation-subst-adopted',
          'bcDetailedLevel-mitigation', 'bcDetailedLevel-mitigation-subst-adopted',
          'constructionG3-mitigation', 'constructionG3-mitigation-subst-adopted'
      )
      AND (
          ui_table_key LIKE 'component%'
          OR (extra_fields->>'emissions_category' = 'Materials')
      )

    UNION ALL

    -- concrete registers and asset: total_emissions_tco2e
    SELECT COALESCE(SUM(
        COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)
    ), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key IN (
          'concreteRegSimplified-mitigation', 'concreteRegSimplified-mitigation-subst-adopted',
          'concreteRegDetailed-mitigation', 'concreteRegDetailed-mitigation-subst-adopted',
          'asset-mitigation', 'asset-mitigation-subst-adopted'
      )
),

-- ── A4 mitigation ────────────────────────────────────────────────────────────
-- Sources: component, bcDetailedLevel (Materials), constructionG3 (Materials)
-- Field: transport_stage_a4_tco2e
mit_a4 AS (
    SELECT COALESCE(SUM(
        COALESCE(NULLIF(NULLIF(extra_fields->>'transport_stage_a4_tco2e', ''), '-')::numeric, 0)
    ), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key IN (
          'component-mitigation', 'component-mitigation-subst-adopted',
          'bcDetailedLevel-mitigation', 'bcDetailedLevel-mitigation-subst-adopted',
          'constructionG3-mitigation', 'constructionG3-mitigation-subst-adopted'
      )
      AND (
          ui_table_key LIKE 'component%'
          OR (extra_fields->>'emissions_category' = 'Materials')
      )
),

-- ── A5 construction mitigation ───────────────────────────────────────────────
-- Sources:
--   component/bcDetailedLevel/constructionG3 (Materials): construction_stage_a5_tco2e
--   bcDetailedLevel/constructionG3 (non-Materials, non-Vegetation, non-Offset): total_emissions_tco2e
--   electricity mitigation: scope-based tco2e
mit_a5_construction AS (
    -- component/bcDetailedLevel/constructionG3 (Materials): construction_stage_a5_tco2e
    SELECT COALESCE(SUM(
        COALESCE(NULLIF(NULLIF(extra_fields->>'construction_stage_a5_tco2e', ''), '-')::numeric, 0)
    ), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key IN (
          'component-mitigation', 'component-mitigation-subst-adopted',
          'bcDetailedLevel-mitigation', 'bcDetailedLevel-mitigation-subst-adopted',
          'constructionG3-mitigation', 'constructionG3-mitigation-subst-adopted'
      )
      AND (
          ui_table_key LIKE 'component%'
          OR (extra_fields->>'emissions_category' = 'Materials')
      )

    UNION ALL

    -- bcDetailedLevel/constructionG3 non-Materials, non-Vegetation, non-Offset: total_emissions_tco2e
    SELECT COALESCE(SUM(
        COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)
    ), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key IN (
          'bcDetailedLevel-mitigation', 'bcDetailedLevel-mitigation-subst-adopted',
          'constructionG3-mitigation', 'constructionG3-mitigation-subst-adopted'
      )
      AND COALESCE(extra_fields->>'emissions_category', '') NOT IN ('Materials', 'Vegetation', 'Offset')

    UNION ALL

    -- electricity mitigation (scope-based)
    SELECT COALESCE(SUM(
        CASE WHEN :elec_method = 'market'
             THEN COALESCE(NULLIF(NULLIF(extra_fields->>'market_based_tco2e', ''), '-')::numeric, 0)
             ELSE COALESCE(NULLIF(NULLIF(extra_fields->>'location_based_tco2e', ''), '-')::numeric, 0)
        END
    ), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key IN (
          'electricity-mitigation', 'electricity-mitigation-subst-adopted'
      )
),

-- ── A5 land use change mitigation ────────────────────────────────────────────
-- Source: bcDetailedLevel (Vegetation category): total_emissions_tco2e
mit_a5_land_use_change AS (
    SELECT COALESCE(SUM(
        COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)
    ), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key IN (
          'bcDetailedLevel-mitigation', 'bcDetailedLevel-mitigation-subst-adopted'
      )
      AND extra_fields->>'emissions_category' = 'Vegetation'
),

-- ── B1 mitigation ────────────────────────────────────────────────────────────
-- Sources: useB1G2, useB1G3 — total_emissions_tco2e
mit_b1 AS (
    SELECT COALESCE(SUM(
        COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)
    ), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key IN (
          'useB1G2-mitigation', 'useB1G2-mitigation-subst-adopted',
          'useB1G3-mitigation', 'useB1G3-mitigation-subst-adopted'
      )
),

-- ── B2-B5 mitigation ─────────────────────────────────────────────────────────
-- Sources: componentRepl, refurbishment, replDetailed — total_emissions_tco2e
mit_b2_b5 AS (
    SELECT COALESCE(SUM(
        COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)
    ), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key IN (
          'componentRepl-mitigation', 'componentRepl-mitigation-subst-adopted',
          'refurbishment-mitigation', 'refurbishment-mitigation-subst-adopted',
          'replDetailed-mitigation', 'replDetailed-mitigation-subst-adopted'
      )
),

-- ── B6 mitigation ────────────────────────────────────────────────────────────
-- Sources: opEnergy (total_emissions_tco2e), opEnergyDetailed (non-Water, non-Offset), opEnergyElectricity (scope-based)
mit_b6 AS (
    -- opEnergy mitigation: total_emissions_tco2e (no market/location split for opEnergy)
    SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key IN (
          'opEnergy-mitigation', 'opEnergy-mitigation-subst-adopted'
      )

    UNION ALL

    -- opEnergyDetailed mitigation (non-Water, non-Offset): total_emissions_tco2e
    SELECT COALESCE(SUM(
        COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)
    ), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key IN (
          'opEnergyDetailed-mitigation', 'opEnergyDetailed-mitigation-subst-adopted'
      )
      AND COALESCE(extra_fields->>'emissions_category', '') NOT IN ('Water', 'Offset')

    UNION ALL

    -- opEnergyElectricity mitigation (scope-based)
    SELECT COALESCE(SUM(
        CASE WHEN :elec_method = 'market'
             THEN COALESCE(NULLIF(NULLIF(extra_fields->>'market_based_tco2e', ''), '-')::numeric, 0)
             ELSE COALESCE(NULLIF(NULLIF(extra_fields->>'location_based_tco2e', ''), '-')::numeric, 0)
        END
    ), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key IN (
          'opEnergyElectricity-mitigation', 'opEnergyElectricity-mitigation-subst-adopted'
      )
),

-- ── B7 mitigation ────────────────────────────────────────────────────────────
-- Source: opEnergyDetailed (Water category): total_emissions_tco2e
mit_b7 AS (
    SELECT COALESCE(SUM(
        COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)
    ), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key IN (
          'opEnergyDetailed-mitigation', 'opEnergyDetailed-mitigation-subst-adopted'
      )
      AND extra_fields->>'emissions_category' = 'Water'
),

-- ════════════════════════════════════════════════════════════════════════════
-- SHORTCUT BASELINE ADJUSTMENTS
-- For shortcut rows the Baseline uses Base Case values; the difference between
-- Base Case and Actual Case represents the additional baseline contribution.
-- ════════════════════════════════════════════════════════════════════════════

-- shortcutIsMaterials delta → allocated to A1-A3
-- Non-maintenance rows only; delta = base_case - actual_case
shortcut_is_mat_delta AS (
    SELECT COALESCE(SUM(
        COALESCE(NULLIF(NULLIF(extra_fields->>'base_case', ''), '-')::numeric, 0) -
        COALESCE(NULLIF(NULLIF(extra_fields->>'actual_case', ''), '-')::numeric, 0)
    ), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'shortcutIsMaterials'
      AND (extra_fields->>'row_type' IS DISTINCT FROM 'maintenance')
),

-- shortcutSat4p A1-A3 delta (Construction materials source)
shortcut_sat4p_a1a3_delta AS (
    SELECT COALESCE(SUM(
        COALESCE(NULLIF(NULLIF(extra_fields->>'base_scope1', ''), '-')::numeric, 0) +
        COALESCE(NULLIF(NULLIF(extra_fields->>'base_scope2', ''), '-')::numeric, 0) -
        COALESCE(NULLIF(NULLIF(extra_fields->>'actual_scope3', ''), '-')::numeric, 0) -
        COALESCE(NULLIF(NULLIF(extra_fields->>'actual_scope4', ''), '-')::numeric, 0)
    ), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'shortcutSat4p'
      AND extra_fields->>'source' = 'Construction materials'
),

-- shortcutSat4p A4 delta (Transport of construction materials source)
shortcut_sat4p_a4_delta AS (
    SELECT COALESCE(SUM(
        COALESCE(NULLIF(NULLIF(extra_fields->>'base_scope1', ''), '-')::numeric, 0) +
        COALESCE(NULLIF(NULLIF(extra_fields->>'base_scope2', ''), '-')::numeric, 0) -
        COALESCE(NULLIF(NULLIF(extra_fields->>'actual_scope3', ''), '-')::numeric, 0) -
        COALESCE(NULLIF(NULLIF(extra_fields->>'actual_scope4', ''), '-')::numeric, 0)
    ), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'shortcutSat4p'
      AND extra_fields->>'source' = 'Transport (construction materials)'
),

-- shortcutSat4p A5 delta (all other sources — construction processes, waste, etc.)
shortcut_sat4p_a5_delta AS (
    SELECT COALESCE(SUM(
        COALESCE(NULLIF(NULLIF(extra_fields->>'base_scope1', ''), '-')::numeric, 0) +
        COALESCE(NULLIF(NULLIF(extra_fields->>'base_scope2', ''), '-')::numeric, 0) -
        COALESCE(NULLIF(NULLIF(extra_fields->>'actual_scope3', ''), '-')::numeric, 0) -
        COALESCE(NULLIF(NULLIF(extra_fields->>'actual_scope4', ''), '-')::numeric, 0)
    ), 0) AS val
    FROM activity_data
    WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'shortcutSat4p'
      AND extra_fields->>'source' NOT IN ('Construction materials', 'Transport (construction materials)')
)

-- ════════════════════════════════════════════════════════════════════════════
-- FINAL SELECT — one row with Actual and Baseline per module
-- Actual  = regular data entry (TIER 1 + TIER 2 + TIER 4)
-- Baseline = Actual + mitigation contributions + shortcut deltas
-- Biogenic (stored carbon) = same for both Baseline and Actual
-- ════════════════════════════════════════════════════════════════════════════

SELECT
    -- ── A1-A3 excluding biogenic ──────────────────────────────────────────
    (SELECT val FROM er_a1a3) + (SELECT val FROM uplift_a1a3)
        AS actual_a1a3,
    (SELECT val FROM er_a1a3) + (SELECT val FROM uplift_a1a3)
        + (SELECT COALESCE(SUM(val), 0) FROM mit_a1a3)
        + (SELECT val FROM shortcut_is_mat_delta)
        + (SELECT val FROM shortcut_sat4p_a1a3_delta)
        AS baseline_a1a3,

    -- ── A1-A3 biogenic (stored carbon — injected in Python from _CARBON_STORAGE_DETAIL_SQL)
    0::numeric AS biogenic,

    -- ── A4 ───────────────────────────────────────────────────────────────
    (SELECT val FROM er_a4) + (SELECT val FROM uplift_a4)
        AS actual_a4,
    (SELECT val FROM er_a4) + (SELECT val FROM uplift_a4)
        + (SELECT val FROM mit_a4)
        + (SELECT val FROM shortcut_sat4p_a4_delta)
        AS baseline_a4,

    -- ── A5 construction (excl. vegetation) ───────────────────────────────
    (SELECT val FROM er_a5) - (SELECT val FROM er_a5_vegetation)
        + (SELECT val FROM er_a5_elec) + (SELECT val FROM uplift_a5)
        AS actual_a5_construction,
    (SELECT val FROM er_a5) - (SELECT val FROM er_a5_vegetation)
        + (SELECT val FROM er_a5_elec) + (SELECT val FROM uplift_a5)
        + (SELECT COALESCE(SUM(val), 0) FROM mit_a5_construction)
        + (SELECT val FROM shortcut_sat4p_a5_delta)
        AS baseline_a5_construction,

    -- ── A5 land use change (vegetation only) ─────────────────────────────
    (SELECT val FROM er_a5_vegetation)
        AS actual_a5_luc,
    (SELECT val FROM er_a5_vegetation)
        + (SELECT val FROM mit_a5_land_use_change)
        AS baseline_a5_luc,

    -- ── B1.1 — Use - material emissions and removals (no data source; always zero) ───────
    0::numeric AS actual_b1_1,
    0::numeric AS baseline_b1_1,

    -- ── B1.2 — Use - operational processes (useB1G2, useB1G3) ───────────────
    (SELECT val FROM b1) + (SELECT val FROM uplift_b1)
        AS actual_b1_2,
    (SELECT val FROM b1) + (SELECT val FROM uplift_b1)
        + (SELECT val FROM mit_b1)
        AS baseline_b1_2,

    -- ── B2-B5 ────────────────────────────────────────────────────────────
    (SELECT val FROM b2_b5) + (SELECT val FROM uplift_b2_b5)
        AS actual_b2_b5,
    (SELECT val FROM b2_b5) + (SELECT val FROM uplift_b2_b5)
        + (SELECT val FROM mit_b2_b5)
        AS baseline_b2_b5,

    -- ── B6 ───────────────────────────────────────────────────────────────
    (SELECT val FROM b6_op) + (SELECT val FROM b6_detailed)
        + (SELECT val FROM er_b6_elec) + (SELECT val FROM uplift_b6)
        AS actual_b6,
    (SELECT val FROM b6_op) + (SELECT val FROM b6_detailed)
        + (SELECT val FROM er_b6_elec) + (SELECT val FROM uplift_b6)
        + (SELECT COALESCE(SUM(val), 0) FROM mit_b6)
        AS baseline_b6,

    -- ── B7 ───────────────────────────────────────────────────────────────
    (SELECT val FROM b7) + (SELECT val FROM uplift_b7)
        AS actual_b7,
    (SELECT val FROM b7) + (SELECT val FROM uplift_b7)
        + (SELECT val FROM mit_b7)
        AS baseline_b7,

    -- ── B8 (no mitigation for users) ─────────────────────────────────────
    (SELECT val FROM b8) AS actual_b8,
    (SELECT val FROM b8) AS baseline_b8
""")


# ─────────────────────────────────────────────────────────────────────────────
# Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/lca-module-breakdown",
    response_model=ITMMReportingResponse,
    summary="ITMM Reporting: LCA module breakdown (Baseline vs Actual)",
)
async def get_ittm_lca_module_breakdown(
    project_id:           UUID = Query(..., description="Project UUID"),
    stage_instance_id:    UUID = Query(..., description="Project stage instance UUID"),
    elec_method:          str  = Query("location", description="Electricity accounting: 'location' or 'market'"),
    project_option_id:    Optional[UUID] = Query(None, description="Project option UUID (optional filter)"),
    submission_period_id: Optional[UUID] = Query(None, description="Submission period UUID (optional filter)"),
    db: AsyncSession = Depends(get_session),
) -> ITMMReportingResponse:
    """
    Returns the ITMM Reporting LCA Module Breakdown table, comparing Baseline
    vs Actual emissions per lifecycle module.

    Each row includes:
    - absolute values (tCO2e)
    - per declared unit values (tCO2e / declared unit), if a declared unit is configured
    - difference (baseline - actual)
    - reduction percentage (difference / baseline × 100)

    Subtotal rows (is_subtotal=True) are computed in Python from their constituent
    module rows and do not have separate SQL columns.

    Electricity emissions respect the ``elec_method`` toggle:
    - 'location' (default): location-based accounting
    - 'market': market-based accounting (GreenPower / RECs)
    """
    if elec_method not in ("location", "market"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="elec_method must be 'location' or 'market'",
        )

    jurisdiction = await ProjectContextHelper.fetch_jurisdiction(db, project_id)
    project = await ProjectContextHelper.fetch_project(db, project_id)

    declared_unit_value: Optional[Decimal] = (
        Decimal(str(project.declared_unit_value))
        if project.declared_unit_value is not None
        else None
    )
    declared_unit_type: Optional[str] = project.declared_unit_type

    params = {
        "project_id":           str(project_id),
        "stage_instance_id":    str(stage_instance_id),
        "elec_method":          elec_method,
        "jurisdiction":         jurisdiction,
        "project_option_id":    str(project_option_id)    if project_option_id    else None,
        "submission_period_id": str(submission_period_id) if submission_period_id else None,
    }

    result = await db.execute(_ITMM_SQL, params)
    _raw = result.mappings().fetchone()

    def _dec(val) -> Decimal:
        if val is None:
            return Decimal(0)
        return Decimal(str(val))

    # Convert to mutable dict so biogenic can be injected
    row: dict = dict(_raw) if _raw is not None else {}

    # Biogenic (stored carbon): delegate to _CARBON_STORAGE_DETAIL_SQL — same calculation as
    # /api/dashboard/carbon-storage/detail. EF values in the views are already negative
    # (sequestration), so the sum is negative (representing sequestered carbon).
    cs_result = await db.execute(_CARBON_STORAGE_DETAIL_SQL, params)
    row["biogenic"] = sum(
        (_dec(r["carbon_storage_tco2e"]) for r in cs_result.mappings().all()),
        Decimal(0),
    )

    actual_a1a3           = _dec(row.get("actual_a1a3"))
    baseline_a1a3         = _dec(row.get("baseline_a1a3"))
    biogenic              = _dec(row.get("biogenic"))
    actual_a4             = _dec(row.get("actual_a4"))
    baseline_a4           = _dec(row.get("baseline_a4"))
    actual_a5_construction  = _dec(row.get("actual_a5_construction"))
    baseline_a5_construction = _dec(row.get("baseline_a5_construction"))
    actual_a5_luc         = _dec(row.get("actual_a5_luc"))
    baseline_a5_luc       = _dec(row.get("baseline_a5_luc"))
    actual_b1_1           = _dec(row.get("actual_b1_1"))
    baseline_b1_1         = _dec(row.get("baseline_b1_1"))
    actual_b2_b5          = _dec(row.get("actual_b2_b5"))
    baseline_b2_b5        = _dec(row.get("baseline_b2_b5"))
    actual_b6             = _dec(row.get("actual_b6"))
    baseline_b6           = _dec(row.get("baseline_b6"))
    actual_b7             = _dec(row.get("actual_b7"))
    baseline_b7           = _dec(row.get("baseline_b7"))
    actual_b8             = _dec(row.get("actual_b8"))
    baseline_b8           = _dec(row.get("baseline_b8"))

    # Subtotals (computed in Python)
    actual_upfront   = actual_a1a3 + actual_a4 + actual_a5_construction + actual_a5_luc
    baseline_upfront = baseline_a1a3 + baseline_a4 + baseline_a5_construction + baseline_a5_luc

    actual_in_use_embodied   = actual_b1_1 + actual_b2_b5
    baseline_in_use_embodied = baseline_b1_1 + baseline_b2_b5

    # B1.2 — Use - operational processes (useB1G2/useB1G3)
    actual_b1_2   = _dec(row.get("actual_b1_2"))
    baseline_b1_2 = _dec(row.get("baseline_b1_2"))

    actual_in_use_operational   = actual_b1_2 + actual_b6 + actual_b7
    baseline_in_use_operational = baseline_b1_2 + baseline_b6 + baseline_b7

    def _make_row(
        code: str,
        label: str,
        actual_abs: Decimal,
        baseline_abs: Decimal,
        is_subtotal: bool = False,
    ) -> ITMMModuleRow:
        """Build one ITMMModuleRow, computing per-unit and percentage columns."""
        du = declared_unit_value

        actual_per: Optional[Decimal] = (
            (actual_abs / du) if du and du != Decimal(0) else None
        )
        baseline_per: Optional[Decimal] = (
            (baseline_abs / du) if du and du != Decimal(0) else None
        )

        diff_abs = baseline_abs - actual_abs
        diff_per: Optional[Decimal] = (
            (baseline_per - actual_per) if (baseline_per is not None and actual_per is not None) else None
        )

        pct_abs: Optional[Decimal] = (
            (diff_abs / baseline_abs * Decimal(100))
            if baseline_abs != Decimal(0) else None
        )
        pct_per: Optional[Decimal] = (
            (diff_per / baseline_per * Decimal(100))
            if (baseline_per is not None and baseline_per != Decimal(0)) else None
        )

        return ITMMModuleRow(
            module_code=code,
            module_label=label,
            is_subtotal=is_subtotal,
            baseline_absolute=baseline_abs,
            baseline_per_unit=baseline_per,
            actual_absolute=actual_abs,
            actual_per_unit=actual_per,
            difference_absolute=diff_abs,
            difference_per_unit=diff_per,
            reduction_pct_absolute=pct_abs,
            reduction_pct_per_unit=pct_per,
        )

    rows: List[ITMMModuleRow] = [
        _make_row(
            "a1_a3_excl_biogenic",
            "Product stage (A1-A3) - excl biogenic carbon",
            actual_a1a3,
            baseline_a1a3,
        ),
        _make_row(
            "a1_a3_biogenic",
            "Product stage (A1-A3) - sequestered biogenic carbon",
            biogenic,
            biogenic,  # same for both
        ),
        _make_row(
            "a4",
            "Transport to site (A4)",
            actual_a4,
            baseline_a4,
        ),
        _make_row(
            "a5_construction",
            "Construction (A5)",
            actual_a5_construction,
            baseline_a5_construction,
        ),
        _make_row(
            "a5_land_use_change",
            "Land use change (A5)",
            actual_a5_luc,
            baseline_a5_luc,
        ),
        _make_row(
            "total_upfront",
            "Total upfront carbon (A1-A5) - excl biogenic carbon",
            actual_upfront,
            baseline_upfront,
            is_subtotal=True,
        ),
        _make_row(
            "b1_1",
            "Use - material emissions and removals (B1.1)",
            actual_b1_1,
            baseline_b1_1,
        ),
        _make_row(
            "b2_b5",
            "Maintenance (B2), Repair (B3), Refurbishment and replacement (B4-B5)",
            actual_b2_b5,
            baseline_b2_b5,
        ),
        _make_row(
            "total_in_use_embodied",
            "Total in-use embodied carbon (B1.1, B2-B5)",
            actual_in_use_embodied,
            baseline_in_use_embodied,
            is_subtotal=True,
        ),
        _make_row(
            "b1_2",
            "Use - operational processes (B1.2)",
            actual_b1_2,
            baseline_b1_2,
        ),
        _make_row(
            "b6",
            "Operational energy (B6)",
            actual_b6,
            baseline_b6,
        ),
        _make_row(
            "b7",
            "Operational water (B7)",
            actual_b7,
            baseline_b7,
        ),
        _make_row(
            "total_in_use_operational",
            "Total in-use operational carbon (B1.2, B6-B7)",
            actual_in_use_operational,
            baseline_in_use_operational,
            is_subtotal=True,
        ),
        _make_row(
            "b8",
            "Users (B8)",
            actual_b8,
            baseline_b8,
        ),
    ]

    return ITMMReportingResponse(
        declared_unit_value=declared_unit_value,
        declared_unit_type=declared_unit_type,
        rows=rows,
    )

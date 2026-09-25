"""
routers/org_dashboard_emissions_breakdown.py

Organisational Dashboard — Emissions Breakdown

Aggregates emissions breakdown data across all projects belonging to the given
organisation, with optional filters by project class, program name, submission
stage, electricity accounting method, and jurisdiction.

Two endpoints:
  GET /api/org-dashboard/emissions-breakdown/summary  — module totals, source categories, headline KPI
  GET /api/org-dashboard/emissions-breakdown/detail   — per-project module breakdown
"""

import re
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from services._calc_utils import DashboardBase
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from models.organizations import Organization

router = APIRouter(
    prefix="/api/org-dashboard/emissions-breakdown",
    tags=["Org Dashboard - Emissions Breakdown"],
)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class OrgModuleRow(DashboardBase):
    """Org-level aggregate per lifecycle module."""
    code: str    # e.g. "A1", "A4", "B2", "Offsets", "Stored carbon"
    label: str   # display label, e.g. "A1-A3 Raw material supply, transport & manufacturing"
    value: Decimal


class OrgSourceCategoryRow(DashboardBase):
    category: str
    value: Decimal


class SummaryIndicator(DashboardBase):
    value: Decimal
    unit: str


class OrgSummaryIndicators(DashboardBase):
    primaryIndicator: Optional[SummaryIndicator] = None    # Upfront intensity per declared unit (A1-A5 / declared unit)
    secondaryIndicator: Optional[SummaryIndicator] = None  # Upfront intensity per CAPEX ($M) (A1-A5 / $M)


class OrgEmissionsBreakdownSummaryResponse(DashboardBase):
    modules: List[OrgModuleRow]
    sourceCategories: List[OrgSourceCategoryRow]
    summaryIndicators: Optional[OrgSummaryIndicators] = None


class OrgEmissionsBreakdownDetailRow(DashboardBase):
    """One row per project showing lifecycle module totals."""
    project_id: UUID
    project_name: str
    a1_a3: Decimal
    a4: Decimal
    a5: Decimal
    b1: Decimal
    b2_b5: Decimal
    b6: Decimal
    b7: Decimal
    b8: Decimal
    offsets: Decimal
    stored_carbon: Decimal
    gross_total_tco2e: Decimal      # a1_a3+a4+a5+b1+b2_b5+b6+b7+b8
    net_total_tco2e: Decimal        # gross + offsets + stored_carbon


class OrgEmissionsBreakdownDetailResponse(DashboardBase):
    rows: List[OrgEmissionsBreakdownDetailRow]


# ---------------------------------------------------------------------------
# Jurisdiction helper
# ---------------------------------------------------------------------------

async def _fetch_org_jurisdiction(db: AsyncSession, org_id: UUID) -> str:
    """Return the jurisdiction name for the organisation. Falls back to 'Australia'."""
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalars().first()
    if org and org.jurisdiction:
        return org.jurisdiction.name
    return "Australia"


# ---------------------------------------------------------------------------
# Bind-params helper
# ---------------------------------------------------------------------------

def _bind(
    org_id: UUID,
    project_class: Optional[str] = None,
    program_name: Optional[str] = None,
    stage: Optional[str] = None,
    elec_method: str = "location",
    jurisdiction: str = "Australia",
    project_type_id: Optional[UUID] = None,
    project_typecast_id: Optional[UUID] = None,
    project_option_id: Optional[UUID] = None,
) -> dict:
    return {
        "org_id": str(org_id),
        "project_class": project_class,
        "program_name": program_name,
        "stage": stage,
        "elec_method": elec_method,
        "jurisdiction": jurisdiction,
        "project_type_id": str(project_type_id) if project_type_id else None,
        "project_typecast_id": str(project_typecast_id) if project_typecast_id else None,
        "project_option_id": str(project_option_id) if project_option_id else None,
        "submission_period_id": None,
    }


def _normalize_enum_filter(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", value.strip()).strip("_").upper()
    return normalized or None


def _normalize_project_class(value: Optional[str]) -> Optional[str]:
    normalized = _normalize_enum_filter(value)
    if normalized in {"SMALL", "LARGE", "RECURRING"}:
        return normalized
    return value.strip() if value else None


def _normalize_stage(value: Optional[str]) -> Optional[str]:
    normalized = _normalize_enum_filter(value)
    if normalized in {"BUSINESS_CASE", "DESIGN", "CONSTRUCTION", "RECURRING"}:
        return normalized
    return value.strip() if value else None


def _normalize_elec_method(value: str) -> str:
    normalized = _normalize_enum_filter(value)
    if normalized in {"LOCATION", "LOCATION_BASED"}:
        return "location"
    if normalized in {"MARKET", "MARKET_BASED"}:
        return "market"
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="elec_method must be 'location', 'market', 'Location-based', or 'Market-based'",
    )


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

_ORG_MODULE_SQL = text("""
WITH
eligible_projects AS (
    SELECT DISTINCT
        p.id           AS project_id,
        p.project_name AS project_name,
        psi.id         AS stage_instance_id
    FROM project p
    JOIN project_stage_instances psi ON psi.project_id = p.id
    WHERE p.is_active = TRUE
      AND (
          p.proponent_org_id = :org_id
          OR EXISTS (
              SELECT 1 FROM project_organizations po
              WHERE po.project_id = p.id
                AND po.organization_id = :org_id
          )
      )
      AND (CAST(:project_class AS TEXT) IS NULL OR p.project_class::text = CAST(:project_class AS TEXT))
      AND (CAST(:program_name AS TEXT) IS NULL OR LOWER(p.program_name) = LOWER(CAST(:program_name AS TEXT)))
      AND (CAST(:stage AS TEXT) IS NULL OR psi.stage::text = CAST(:stage AS TEXT))
      AND (CAST(:project_type_id AS uuid) IS NULL OR p.project_type_id = CAST(:project_type_id AS uuid))
    AND (CAST(:project_typecast_id AS uuid) IS NULL OR p.project_typecast_id = CAST(:project_typecast_id AS uuid))
),

-- ════════════════════════════════════════════════════════════════════════════
-- TIER 3 — Stored carbon (view JOINs, no value_key yet)
-- Mirrors project-level g2_stored_carbon and g34_carbon_storage CTEs.
-- Replace with emissions_results JOIN once developer adds a stored-carbon code.
-- ════════════════════════════════════════════════════════════════════════════

g2_stored_carbon AS (
    SELECT
        ep.project_id,
        ep.project_name,
        -- EF is already negative in v_grade2_component_level; no extra negation needed
        COALESCE(g2."Carbon Storage (tCO2e/UoM)", 0) * COALESCE(ad.quantity, 0) AS stored_carbon
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id        = ad.project_id
       AND ep.stage_instance_id = ad.project_stage_instance_id
    LEFT JOIN v_grade2_component_level g2
        ON  g2."Jurisdiction"           = :jurisdiction
        AND g2."Emissions Category"     = COALESCE(NULLIF(ad.extra_fields->>'emissions_category',    ''), '__no_match__')
        AND g2."Emissions Sub-Category" = COALESCE(NULLIF(ad.extra_fields->>'emissions_subcategory', ''), '__no_match__')
        AND g2."Emissions Source"       = COALESCE(NULLIF(ad.extra_fields->>'emissions_source_name', ''), '__no_match__')
    WHERE ad.ui_table_key = 'component'
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
),

g34_carbon_storage AS (
    SELECT
        ep.project_id,
        ep.project_name,
        -- EF is already negative in v_grade34_detailed_level; no extra negation needed
        COALESCE(g34."Carbon Storage (tCO2e/UoM)", 0) * COALESCE(ad.quantity, 0) AS stored_carbon
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id        = ad.project_id
       AND ep.stage_instance_id = ad.project_stage_instance_id
    LEFT JOIN v_grade34_detailed_level g34
        ON  g34."Jurisdiction"           = :jurisdiction
        AND g34."Emissions Category"     = COALESCE(NULLIF(ad.extra_fields->>'emissions_category',    ''), '__no_match__')
        AND g34."Emissions Sub-Category" = COALESCE(NULLIF(ad.extra_fields->>'emissions_subcategory', ''), '__no_match__')
        AND g34."Emissions Source"       = COALESCE(NULLIF(ad.extra_fields->>'emissions_source_name', ''), '__no_match__')
        AND g34."UoM"                    = COALESCE(NULLIF(ad.extra_fields->>'unit_code',              ''), '__no_match__')
    WHERE ad.ui_table_key = 'bcDetailedLevel'
      AND COALESCE(ad.extra_fields->>'emissions_category', '') <> 'Offset'
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
),

-- Pre-deduplicated largeRoadParams per project: final_user_emissions_tco2e repeats
-- across modelled years for the same parameter combination. Take MAX per combination
-- then sum across combinations, grouped by project.
b8_large_road_deduped AS (
    SELECT t.project_id, t.project_stage_instance_id, SUM(t.max_val) AS val
    FROM (
        SELECT
            ad.project_id,
            ad.project_stage_instance_id,
            MAX(COALESCE(NULLIF(NULLIF(ad.extra_fields->>'final_user_emissions_tco2e', ''), '-')::numeric, 0)) AS max_val
        FROM activity_data ad
        JOIN eligible_projects ep
            ON ep.project_id = ad.project_id AND ep.stage_instance_id = ad.project_stage_instance_id
        WHERE ad.ui_table_key = 'largeRoadParams'
          AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
          AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
        GROUP BY
            ad.project_id,
            ad.project_stage_instance_id,
            ad.extra_fields->>'gradient',
            ad.extra_fields->>'curvature',
            ad.extra_fields->>'roughness',
            ad.extra_fields->>'ev_uptake_scenario'
    ) t
    GROUP BY t.project_id, t.project_stage_instance_id
),

-- Flat contributions: (project_id, project_name, module_columns…)
module_rows AS (

    -- ════════════════════════════════════════════════════════════════════════
    -- TIER 1 — emissions_results JOIN (canonical per-module tCO2e)
    -- Mirrors project-level _MODULE_SQL TIER 1 CTEs expanded across all org projects.
    -- The developer stores the correct A1-A3/A4/A5 split in emissions_results for
    -- all input levels (Grade 1 asset, Grade 2 component, Grade 3/4 detailed,
    -- concrete registers, shortcut IS Materials, etc.).
    -- NOTE: SAT4P A5 rows are NOT in emissions_results — handled separately below.
    -- NOTE: electricity A5 rows are excluded from row 3 and handled in row 4.
    -- ════════════════════════════════════════════════════════════════════════

    -- 1. A1-A3 from emissions_results (all input levels)
    SELECT ep.project_id, ep.project_name,
        COALESCE(er.value, 0) AS a1_a3,
        0::numeric AS a4, 0::numeric AS a5, 0::numeric AS b1, 0::numeric AS b2_b5,
        0::numeric AS b6, 0::numeric AS b7, 0::numeric AS b8,
        0::numeric AS offsets, 0::numeric AS stored_carbon
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id = ad.project_id AND ep.stage_instance_id = ad.project_stage_instance_id
    JOIN emissions_results er ON er.activity_data_id = ad.id
        AND er.value_key = 'A1-A3'
    WHERE (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

    UNION ALL

    -- 2. A4 from emissions_results
    SELECT ep.project_id, ep.project_name,
        0, COALESCE(er.value, 0), 0, 0, 0, 0, 0, 0, 0, 0
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id = ad.project_id AND ep.stage_instance_id = ad.project_stage_instance_id
    JOIN emissions_results er ON er.activity_data_id = ad.id
        AND er.value_key = 'A4'
    WHERE (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

    UNION ALL

    -- 3. A5 non-electricity from emissions_results
    -- Excludes electricity rows (ui_table_key='electricity') — those are in row 4.
    SELECT ep.project_id, ep.project_name,
        0, 0, COALESCE(er.value, 0), 0, 0, 0, 0, 0, 0, 0
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id = ad.project_id AND ep.stage_instance_id = ad.project_stage_instance_id
    JOIN emissions_results er ON er.activity_data_id = ad.id
        AND er.value_key = 'A5'
    WHERE (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
            AND ad.ui_table_key NOT LIKE 'electricity%'
            AND ad.ui_table_key NOT LIKE 'opEnergyElectricity%'

    UNION ALL

    -- 4. A5 construction electricity (extra_fields: market_based_tco2e / location_based_tco2e)
    SELECT ep.project_id, ep.project_name,
        0, 0,
        CASE WHEN :elec_method = 'market'
             THEN COALESCE(NULLIF(NULLIF(ad.extra_fields->>'market_based_tco2e',   ''), '-')::numeric, 0)
             ELSE COALESCE(NULLIF(NULLIF(ad.extra_fields->>'location_based_tco2e', ''), '-')::numeric, 0)
        END,
        0, 0, 0, 0, 0, 0, 0
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id = ad.project_id AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE ad.ui_table_key = 'electricity'
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

    UNION ALL

    -- 4b. A5 SAT4P shortcut (only the 3 A5-specific sources)
    -- 'Construction materials' → A1-A3, 'Transport (construction materials)' → A4,
    -- 'Maintenance processes / equipment' / 'Transport (maintenance materials)' → B2-B5,
    -- 'Use phase' → B8 — all excluded by using an explicit IN list.
    SELECT ep.project_id, ep.project_name,
        0, 0,
        COALESCE(NULLIF(NULLIF(ad.extra_fields->>'actual_scope3', ''), '-')::numeric, 0) +
        COALESCE(NULLIF(NULLIF(ad.extra_fields->>'actual_scope4', ''), '-')::numeric, 0),
        0, 0, 0, 0, 0, 0, 0
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id = ad.project_id AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE ad.ui_table_key = 'shortcutSat4p'
      AND ad.extra_fields->>'source' IN (
          'Construction processes/equipment',
          'Disposal',
          'Transport off-site (waste)'
      )
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

    UNION ALL

    -- 5. B2-B5 from extra_fields (componentRepl + refurbishment + replDetailed non-Offset)
    --   componentRepl → Component Level Replacement (B4) (Grade 2 and 3)
    --   refurbishment → Other Maintenance/Repair/Replacement/Refurbishment Activities (Grade 2)
    --   replDetailed  → Detailed Level (Grade 3)
    SELECT ep.project_id, ep.project_name,
        0, 0, 0, 0,
        COALESCE(NULLIF(NULLIF(ad.extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0),
        0, 0, 0, 0, 0
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id = ad.project_id AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE ad.ui_table_key IN ('componentRepl', 'refurbishment', 'replDetailed')
      AND NOT (ad.ui_table_key = 'replDetailed' AND COALESCE(ad.extra_fields->>'emissions_category', '') = 'Offset')
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

    UNION ALL

    -- 6. B6 operational electricity (extra_fields: market_based_tco2e / location_based_tco2e)
    SELECT ep.project_id, ep.project_name,
        0, 0, 0, 0, 0,
        CASE WHEN :elec_method = 'market'
             THEN COALESCE(NULLIF(NULLIF(ad.extra_fields->>'market_based_tco2e',   ''), '-')::numeric, 0)
             ELSE COALESCE(NULLIF(NULLIF(ad.extra_fields->>'location_based_tco2e', ''), '-')::numeric, 0)
        END,
        0, 0, 0, 0
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id = ad.project_id AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE ad.ui_table_key = 'opEnergyElectricity'
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

    UNION ALL

    -- ════════════════════════════════════════════════════════════════════════
    -- TIER 2 — modules not yet in emissions_results (extra_fields fallback)
    -- ════════════════════════════════════════════════════════════════════════

    -- 7. B1 (useB1G2, useB1G3)
    SELECT ep.project_id, ep.project_name,
        0, 0, 0,
        COALESCE(NULLIF(NULLIF(ad.extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0),
        0, 0, 0, 0, 0, 0
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id = ad.project_id AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE ad.ui_table_key IN ('useB1G2', 'useB1G3')
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

    UNION ALL

    -- 8. B6 opEnergy (Component Level, Grade 2): use operational total based on elec_method.
    --    Prefer method-specific total, with total_emissions_tco2e as fallback.
    SELECT ep.project_id, ep.project_name,
        0, 0, 0, 0, 0,
        CASE WHEN :elec_method = 'market'
             THEN COALESCE(
                     NULLIF(NULLIF(ad.extra_fields->>'market_based_total_tco2e', ''), '-')::numeric,
                     COALESCE(NULLIF(NULLIF(ad.extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)
                  )
             ELSE COALESCE(
                     NULLIF(NULLIF(ad.extra_fields->>'location_based_total_tco2e', ''), '-')::numeric,
                     COALESCE(NULLIF(NULLIF(ad.extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)
                  )
        END,
        0, 0, 0, 0
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id = ad.project_id AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE ad.ui_table_key = 'opEnergy'
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

    UNION ALL

    -- 9. B6 opEnergyDetailed non-Water, non-Offset rows (Offset rows are captured in row 12)
    SELECT ep.project_id, ep.project_name,
        0, 0, 0, 0, 0,
        COALESCE(NULLIF(NULLIF(ad.extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0),
        0, 0, 0, 0
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id = ad.project_id AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE ad.ui_table_key = 'opEnergyDetailed'
      AND COALESCE(ad.extra_fields->>'emissions_category', '') NOT IN ('Water', 'Offset')
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

    UNION ALL

    -- 10. B7 opEnergyDetailed Water
    SELECT ep.project_id, ep.project_name,
        0, 0, 0, 0, 0, 0,
        COALESCE(NULLIF(NULLIF(ad.extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0),
        0, 0, 0
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id = ad.project_id AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE ad.ui_table_key = 'opEnergyDetailed'
      AND ad.extra_fields->>'emissions_category' = 'Water'
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

    UNION ALL

    -- 11a. B8 small road users: relativeUserEmissions
    SELECT ep.project_id, ep.project_name,
        0, 0, 0, 0, 0, 0, 0,
        COALESCE(NULLIF(NULLIF(ad.extra_fields->>'relativeUserEmissions', ''), '-')::numeric, 0),
        0, 0
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id = ad.project_id AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE ad.ui_table_key = 'roadUsers'
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

    UNION ALL

    -- 11b. B8 rail users (small and large): emissions_total_ref_period_tco2e
    SELECT ep.project_id, ep.project_name,
        0, 0, 0, 0, 0, 0, 0,
        COALESCE(NULLIF(NULLIF(ad.extra_fields->>'emissions_total_ref_period_tco2e', ''), '-')::numeric, 0),
        0, 0
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id = ad.project_id AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE ad.ui_table_key = 'railUsers'
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

    UNION ALL

    -- 11c. B8 large road users: final_user_emissions_tco2e (pre-deduplicated across modelled years)
    SELECT ep.project_id, ep.project_name,
        0, 0, 0, 0, 0, 0, 0,
        COALESCE(lr.val, 0),
        0, 0
    FROM eligible_projects ep
    JOIN b8_large_road_deduped lr
        ON lr.project_id = ep.project_id AND lr.project_stage_instance_id = ep.stage_instance_id

    UNION ALL

    -- 12. Offsets (stored as negative)
    SELECT ep.project_id, ep.project_name,
        0, 0, 0, 0, 0, 0, 0, 0,
        -COALESCE(NULLIF(NULLIF(ad.extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0),
        0
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id = ad.project_id AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE ad.ui_table_key IN (
        'bcDetailedLevel', 'constructionG3', 'recurringG3',
        'replDetailed', 'opEnergyDetailed'
    )
      AND ad.extra_fields->>'emissions_category' = 'Offset'
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

    UNION ALL

    -- ════════════════════════════════════════════════════════════════════════
    -- TIER 3 — Stored carbon (from pre-computed CTEs)
    -- ════════════════════════════════════════════════════════════════════════

    -- 13. Grade 2 component stored carbon
    SELECT project_id, project_name,
        0, 0, 0, 0, 0, 0, 0, 0, 0, stored_carbon
    FROM g2_stored_carbon

    UNION ALL

    -- 14. Grade 3/4 detailed stored carbon
    SELECT project_id, project_name,
        0, 0, 0, 0, 0, 0, 0, 0, 0, stored_carbon
    FROM g34_carbon_storage

    UNION ALL

    -- ════════════════════════════════════════════════════════════════════════
    -- TIER 4 — completeness upscaling adjustments
    -- ════════════════════════════════════════════════════════════════════════

    -- 15a. A1-A3 upscaling
    SELECT ep.project_id, ep.project_name,
        COALESCE(NULLIF(NULLIF(ad.extra_fields->>'upscaling_adjustment_tco2e', ''), '-')::numeric, 0),
        0, 0, 0, 0, 0, 0, 0, 0, 0
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id = ad.project_id AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE ad.ui_table_key = 'completeness' AND ad.extra_fields->>'module' = 'a1_a3'
      AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

    UNION ALL

    -- 15b. A4 upscaling
    SELECT ep.project_id, ep.project_name,
        0, COALESCE(NULLIF(NULLIF(ad.extra_fields->>'upscaling_adjustment_tco2e', ''), '-')::numeric, 0),
        0, 0, 0, 0, 0, 0, 0, 0
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id = ad.project_id AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE ad.ui_table_key = 'completeness' AND ad.extra_fields->>'module' = 'a4'
      AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

    UNION ALL

    -- 15c. A5 upscaling
    SELECT ep.project_id, ep.project_name,
        0, 0, COALESCE(NULLIF(NULLIF(ad.extra_fields->>'upscaling_adjustment_tco2e', ''), '-')::numeric, 0),
        0, 0, 0, 0, 0, 0, 0
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id = ad.project_id AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE ad.ui_table_key = 'completeness' AND ad.extra_fields->>'module' = 'a5'
      AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

    UNION ALL

    -- 15d. B1 upscaling
    SELECT ep.project_id, ep.project_name,
        0, 0, 0, COALESCE(NULLIF(NULLIF(ad.extra_fields->>'upscaling_adjustment_tco2e', ''), '-')::numeric, 0),
        0, 0, 0, 0, 0, 0
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id = ad.project_id AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE ad.ui_table_key = 'completeness' AND ad.extra_fields->>'module' = 'b1'
      AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

    UNION ALL

    -- 15e. B2-B5 upscaling
    SELECT ep.project_id, ep.project_name,
        0, 0, 0, 0, COALESCE(NULLIF(NULLIF(ad.extra_fields->>'upscaling_adjustment_tco2e', ''), '-')::numeric, 0),
        0, 0, 0, 0, 0
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id = ad.project_id AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE ad.ui_table_key = 'completeness' AND ad.extra_fields->>'module' = 'b2_b5'
      AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

    UNION ALL

    -- 15f. B6 upscaling
    SELECT ep.project_id, ep.project_name,
        0, 0, 0, 0, 0, COALESCE(NULLIF(NULLIF(ad.extra_fields->>'upscaling_adjustment_tco2e', ''), '-')::numeric, 0),
        0, 0, 0, 0
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id = ad.project_id AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE ad.ui_table_key = 'completeness' AND ad.extra_fields->>'module' = 'b6'
      AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

    UNION ALL

    -- 15g. B7 upscaling
    SELECT ep.project_id, ep.project_name,
        0, 0, 0, 0, 0, 0, COALESCE(NULLIF(NULLIF(ad.extra_fields->>'upscaling_adjustment_tco2e', ''), '-')::numeric, 0),
        0, 0, 0
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id = ad.project_id AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE ad.ui_table_key = 'completeness' AND ad.extra_fields->>'module' = 'b7'
      AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

)

SELECT
    project_id,
    project_name,
    SUM(a1_a3)         AS a1_a3,
    SUM(a4)            AS a4,
    SUM(a5)            AS a5,
    SUM(b1)            AS b1,
    SUM(b2_b5)         AS b2_b5,
    SUM(b6)            AS b6,
    SUM(b7)            AS b7,
    SUM(b8)            AS b8,
    SUM(offsets)       AS offsets,
    SUM(stored_carbon) AS stored_carbon
FROM module_rows
GROUP BY project_id, project_name
ORDER BY project_name
""")

_ORG_SOURCE_SQL = text("""
WITH
eligible_projects AS (
    SELECT DISTINCT
        p.id   AS project_id,
        psi.id AS stage_instance_id
    FROM project p
    JOIN project_stage_instances psi ON psi.project_id = p.id
    WHERE p.is_active = TRUE
      AND (
          p.proponent_org_id = :org_id
          OR EXISTS (
              SELECT 1 FROM project_organizations po
              WHERE po.project_id = p.id
                AND po.organization_id = :org_id
          )
      )
      AND (CAST(:project_class AS TEXT) IS NULL OR p.project_class::text = CAST(:project_class AS TEXT))
      AND (CAST(:program_name AS TEXT) IS NULL OR LOWER(p.program_name) = LOWER(CAST(:program_name AS TEXT)))
      AND (CAST(:stage AS TEXT) IS NULL OR psi.stage::text = CAST(:stage AS TEXT))
      AND (CAST(:project_type_id AS uuid) IS NULL OR p.project_type_id = CAST(:project_type_id AS uuid))
    AND (CAST(:project_typecast_id AS uuid) IS NULL OR p.project_typecast_id = CAST(:project_typecast_id AS uuid))
)

SELECT
    category,
    SUM(val) AS emissions_tco2e
FROM (

    -- Grade 3/4 detailed rows
    SELECT
        COALESCE(NULLIF(TRIM(ad.extra_fields->>'emissions_category'), ''), 'Other') AS category,
        COALESCE(NULLIF(NULLIF(ad.extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0) AS val
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id = ad.project_id AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE ad.ui_table_key IN (
        'bcDetailedLevel', 'constructionG3', 'recurringG3',
        'useB1G3', 'replDetailed', 'opEnergyDetailed'
    )
      AND COALESCE(ad.extra_fields->>'emissions_category', '') != 'Offset'
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

    UNION ALL

    -- Grade 2 component rows
    SELECT
        COALESCE(NULLIF(TRIM(ad.extra_fields->>'emissions_category'), ''), 'Other') AS category,
        COALESCE(NULLIF(NULLIF(ad.extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0) AS val
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id = ad.project_id AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE ad.ui_table_key IN ('component', 'componentRepl', 'useB1G2')
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

    UNION ALL

    -- Grade 1 asset rows — classified as 'Materials'
    SELECT
        'Materials'::text AS category,
        COALESCE(NULLIF(NULLIF(ad.extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0) AS val
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id = ad.project_id AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE ad.ui_table_key = 'asset'
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

    UNION ALL

    -- Concrete registers — classified as 'Materials'
    SELECT
        'Materials'::text AS category,
        COALESCE(NULLIF(NULLIF(ad.extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0) AS val
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id = ad.project_id AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE ad.ui_table_key IN ('concreteRegSimplified', 'concreteRegDetailed')
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

    UNION ALL

    -- Refurbishment rows
    SELECT
        COALESCE(NULLIF(TRIM(ad.extra_fields->>'emissions_category'), ''), 'Other') AS category,
        COALESCE(NULLIF(NULLIF(ad.extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0) AS val
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id = ad.project_id AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE ad.ui_table_key = 'refurbishment'
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

    UNION ALL

    -- Construction electricity — classified as 'Electricity'
    SELECT
        'Electricity'::text AS category,
        CASE WHEN :elec_method = 'market'
             THEN COALESCE(NULLIF(NULLIF(ad.extra_fields->>'market_based_tco2e',   ''), '-')::numeric, 0)
             ELSE COALESCE(NULLIF(NULLIF(ad.extra_fields->>'location_based_tco2e', ''), '-')::numeric, 0)
        END AS val
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id = ad.project_id AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE ad.ui_table_key = 'electricity'
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

    UNION ALL

    -- Operational electricity — classified as 'Electricity'
    SELECT
        'Electricity'::text AS category,
        CASE WHEN :elec_method = 'market'
             THEN COALESCE(NULLIF(NULLIF(ad.extra_fields->>'market_based_tco2e',   ''), '-')::numeric, 0)
             ELSE COALESCE(NULLIF(NULLIF(ad.extra_fields->>'location_based_tco2e', ''), '-')::numeric, 0)
        END AS val
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id = ad.project_id AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE ad.ui_table_key = 'opEnergyElectricity'
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

    UNION ALL

    -- opEnergy (Grade 2 operational) — classified as 'Electricity'
    SELECT
        'Electricity'::text AS category,
        CASE WHEN :elec_method = 'market'
             THEN COALESCE(
                     NULLIF(NULLIF(ad.extra_fields->>'market_based_total_tco2e',   ''), '-')::numeric,
                     COALESCE(NULLIF(NULLIF(ad.extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)
                  )
             ELSE COALESCE(
                     NULLIF(NULLIF(ad.extra_fields->>'location_based_total_tco2e', ''), '-')::numeric,
                     COALESCE(NULLIF(NULLIF(ad.extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)
                  )
        END AS val
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id = ad.project_id AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE ad.ui_table_key = 'opEnergy'
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

    UNION ALL

    -- Shortcut IS Materials — classified as 'Materials'
    SELECT
        'Materials'::text AS category,
        COALESCE(NULLIF(NULLIF(ad.extra_fields->>'actual_case', ''), '-')::numeric, 0) AS val
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id = ad.project_id AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE ad.ui_table_key = 'shortcutIsMaterials'
      AND (ad.extra_fields->>'row_type' IS DISTINCT FROM 'maintenance')
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

    UNION ALL

    -- Shortcut SAT4P — source-based category assignment
    SELECT
        CASE ad.extra_fields->>'source'
            WHEN 'Construction materials'             THEN 'Materials'
            WHEN 'Transport (construction materials)' THEN 'Fuels'
            ELSE                                           'Fuels'
        END AS category,
        COALESCE(NULLIF(NULLIF(ad.extra_fields->>'actual_scope3', ''), '-')::numeric, 0) +
        COALESCE(NULLIF(NULLIF(ad.extra_fields->>'actual_scope4', ''), '-')::numeric, 0) AS val
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id = ad.project_id AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE ad.ui_table_key = 'shortcutSat4p'
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

) all_rows
GROUP BY category
HAVING SUM(val) > 0
ORDER BY SUM(val) DESC
""")

_ORG_PROJECT_META_SQL = text("""
WITH
eligible_projects AS (
    SELECT DISTINCT
        p.id,
        p.declared_unit_value,
        p.declared_unit_type,
        p.project_capex_million
    FROM project p
    JOIN project_stage_instances psi ON psi.project_id = p.id
    WHERE p.is_active = TRUE
      AND (
          p.proponent_org_id = :org_id
          OR EXISTS (
              SELECT 1 FROM project_organizations po
              WHERE po.project_id = p.id
                AND po.organization_id = :org_id
          )
      )
      AND (CAST(:project_class AS TEXT) IS NULL OR p.project_class::text = CAST(:project_class AS TEXT))
      AND (CAST(:program_name AS TEXT) IS NULL OR LOWER(p.program_name) = LOWER(CAST(:program_name AS TEXT)))
      AND (CAST(:stage AS TEXT) IS NULL OR psi.stage::text = CAST(:stage AS TEXT))
      AND (CAST(:project_type_id AS uuid) IS NULL OR p.project_type_id = CAST(:project_type_id AS uuid))
      AND (CAST(:project_typecast_id AS uuid) IS NULL OR p.project_typecast_id = CAST(:project_typecast_id AS uuid))
)
SELECT
    declared_unit_value,
    declared_unit_type,
    project_capex_million
FROM eligible_projects
""")


# ---------------------------------------------------------------------------
# Helper: build per-project module rows into summary dicts
# ---------------------------------------------------------------------------

# (code, label, sql_column)
_MODULE_META = [
    ("A1",            "A1-A3 Raw material supply, transport & manufacturing", "a1_a3"),
    ("A2",            "A2 (included in A1-A3)",                              None),
    ("A3",            "A3 (included in A1-A3)",                              None),
    ("A4",            "A4 Transport to site",                                "a4"),
    ("A5",            "A5 Construction installation process",                "a5"),
    ("B1",            "B1 Use",                                              "b1"),
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


def _to_decimal(value) -> Decimal:
    if value is None:
        return Decimal(0)
    return Decimal(str(value))


def _aggregate_module_totals(rows) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = {
        "a1_a3": Decimal(0),
        "a4": Decimal(0),
        "a5": Decimal(0),
        "b1": Decimal(0),
        "b2_b5": Decimal(0),
        "b6": Decimal(0),
        "b7": Decimal(0),
        "b8": Decimal(0),
        "offsets": Decimal(0),
        "stored_carbon": Decimal(0),
    }
    for r in rows:
        for col in totals:
            totals[col] += _to_decimal(r[col])
    return totals


def _build_modules(totals: dict[str, Decimal]) -> list[OrgModuleRow]:
    modules: list[OrgModuleRow] = []
    for code, label, col in _MODULE_META:
        modules.append(OrgModuleRow(
            code=code,
            label=label,
            value=Decimal(0) if col is None else totals[col],
        ))
    return modules


def _build_summary_indicators(totals: dict[str, Decimal], project_meta_rows) -> OrgSummaryIndicators:
    upfront_a1_a5_total = totals["a1_a3"] + totals["a4"] + totals["a5"]

    unit_type_values = {
        (r["declared_unit_type"] or "").strip()
        for r in project_meta_rows
        if (r["declared_unit_type"] or "").strip()
    }
    declared_unit_sum = sum(
        (_to_decimal(r["declared_unit_value"]) for r in project_meta_rows if r["declared_unit_value"] is not None),
        Decimal(0),
    )

    primary: Optional[SummaryIndicator] = None
    if len(unit_type_values) == 1 and declared_unit_sum != 0:
        declared_unit_type = next(iter(unit_type_values))
        primary = SummaryIndicator(
            value=upfront_a1_a5_total / declared_unit_sum,
            unit=f"tCO\u2082e/{declared_unit_type}",
        )

    project_capex_sum = sum(
        (_to_decimal(r["project_capex_million"]) for r in project_meta_rows if r["project_capex_million"] is not None),
        Decimal(0),
    )
    secondary: Optional[SummaryIndicator] = None
    if project_capex_sum != 0:
        secondary = SummaryIndicator(
            value=upfront_a1_a5_total / project_capex_sum,
            unit="tCO\u2082e/$M",
        )

    return OrgSummaryIndicators(primaryIndicator=primary, secondaryIndicator=secondary)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/summary", response_model=OrgEmissionsBreakdownSummaryResponse)
async def org_emissions_breakdown_summary(
    org_id: UUID = Query(..., description="Organisation UUID"),
    project_class: Optional[str] = Query(None),
    program_name: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    elec_method: str = Query("location", description="'location' or 'market'"),
    project_type_id: Optional[UUID] = Query(None, description="Filter by project type (benchmark mastertype UUID)"),
    project_typecast: Optional[UUID] = Query(None, description="Filter by project typecast UUID"),
    project_option_id: Optional[UUID] = Query(None, description="Filter by project option UUID"),
    db: AsyncSession = Depends(get_session),
):
    """Returns emissions by lifecycle module, by source category, and headline KPI across all org projects."""
    jurisdiction = await _fetch_org_jurisdiction(db, org_id)
    normalized_elec_method = _normalize_elec_method(elec_method)
    params = _bind(
        org_id,
        project_class=_normalize_project_class(project_class),
        program_name=program_name,
        stage=_normalize_stage(stage),
        elec_method=normalized_elec_method,
        jurisdiction=jurisdiction,
        project_type_id=project_type_id,
        project_typecast_id=project_typecast,
        project_option_id=project_option_id,
    )
    try:
        module_result = await db.execute(_ORG_MODULE_SQL, params)
        source_result = await db.execute(_ORG_SOURCE_SQL, params)
        meta_result = await db.execute(_ORG_PROJECT_META_SQL, params)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Database query failed: {exc}") from exc

    module_rows = module_result.mappings().all()
    source_rows = source_result.mappings().all()
    project_meta_rows = meta_result.mappings().all()

    totals = _aggregate_module_totals(module_rows)
    modules = _build_modules(totals)

    source_categories = [
        OrgSourceCategoryRow(category=r["category"], value=Decimal(str(r["emissions_tco2e"] or 0)))
        for r in source_rows
    ]

    return OrgEmissionsBreakdownSummaryResponse(
        modules=modules,
        sourceCategories=source_categories,
        summaryIndicators=_build_summary_indicators(totals, project_meta_rows),
    )


@router.get("/detail", response_model=OrgEmissionsBreakdownDetailResponse)
async def org_emissions_breakdown_detail(
    org_id: UUID = Query(..., description="Organisation UUID"),
    project_class: Optional[str] = Query(None),
    program_name: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    elec_method: str = Query("location", description="'location' or 'market'"),
    project_type_id: Optional[UUID] = Query(None, description="Filter by project type (benchmark mastertype UUID)"),
    project_typecast: Optional[UUID] = Query(None, description="Filter by project typecast UUID"),
    project_option_id: Optional[UUID] = Query(None, description="Filter by project option UUID"),
    db: AsyncSession = Depends(get_session),
):
    """Returns per-project lifecycle module breakdown across all projects in the organisation."""
    jurisdiction = await _fetch_org_jurisdiction(db, org_id)
    normalized_elec_method = _normalize_elec_method(elec_method)
    params = _bind(
        org_id,
        project_class=_normalize_project_class(project_class),
        program_name=program_name,
        stage=_normalize_stage(stage),
        elec_method=normalized_elec_method,
        jurisdiction=jurisdiction,
        project_type_id=project_type_id,
        project_typecast_id=project_typecast,
        project_option_id=project_option_id,
    )
    try:
        result = await db.execute(_ORG_MODULE_SQL, params)
        rows = result.mappings().all()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Database query failed: {exc}") from exc

    detail_rows = []
    for r in rows:
        a1_a3     = Decimal(str(r["a1_a3"]     or 0))
        a4        = Decimal(str(r["a4"]        or 0))
        a5        = Decimal(str(r["a5"]        or 0))
        b1        = Decimal(str(r["b1"]        or 0))
        b2_b5     = Decimal(str(r["b2_b5"]     or 0))
        b6        = Decimal(str(r["b6"]        or 0))
        b7        = Decimal(str(r["b7"]        or 0))
        b8        = Decimal(str(r["b8"]        or 0))
        offsets   = Decimal(str(r["offsets"]   or 0))
        stored    = Decimal(str(r["stored_carbon"] or 0))
        gross     = a1_a3 + a4 + a5 + b1 + b2_b5 + b6 + b7 + b8
        detail_rows.append(OrgEmissionsBreakdownDetailRow(
            project_id=r["project_id"],
            project_name=r["project_name"],
            a1_a3=a1_a3,
            a4=a4,
            a5=a5,
            b1=b1,
            b2_b5=b2_b5,
            b6=b6,
            b7=b7,
            b8=b8,
            offsets=offsets,
            stored_carbon=stored,
            gross_total_tco2e=gross,
            net_total_tco2e=gross + offsets + stored,
        ))

    return OrgEmissionsBreakdownDetailResponse(rows=detail_rows)

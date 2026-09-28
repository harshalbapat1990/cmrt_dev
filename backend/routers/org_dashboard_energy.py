"""
routers/org_dashboard_energy.py

Organisational Dashboard — Energy (GJ)

Aggregates energy data across all projects belonging to the given organisation,
with optional filters by project class, program name, and submission stage.

Two endpoints:
  GET /api/org-dashboard/energy/summary  — breakdown by lifecycle stage, input table, sub-category
  GET /api/org-dashboard/energy/detail   — row-level breakdown (includes project info)
"""

import re
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from services._calc_utils import DashboardBase, OUTPUT_DECIMAL_PLACES
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from services.emissions_result_aggregates import emissions_totals_by_activity

router = APIRouter(
    prefix="/api/org-dashboard/energy",
    tags=["Org Dashboard - Energy"],
)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class OrgEnergyFuelByStage(DashboardBase):
    """Energy breakdown by individual source — matches EnergyFuelByStage on project dashboard."""
    emissions_source: str
    renewable_status: str
    construction_gj: Decimal
    inuse_gj: Decimal
    lifecycle_gj: Decimal
    lifecycle_pct: Decimal


class OrgEnergySummaryResponse(DashboardBase):
    """
    Aggregated datasets for the Renewable Energy org-dashboard screen.
    Format matches EnergySummaryResponse on the project dashboard.
    """
    unit: str                                     # always "GJ"
    stages: List[str]                             # ordered stage labels that have data
    absolute: dict                                # {nonRenewable: {stage: gj}, renewable: {stage: gj}}
    percentage: dict                              # {nonRenewable: {stage: pct}, renewable: {stage: pct}}
    by_fuel_source: List[OrgEnergyFuelByStage]    # per-source breakdown


class OrgEnergyDetailRow(DashboardBase):
    id: UUID
    project_id: UUID
    project_name: str
    stage_type: str
    lifecycle_stage: str
    input_table: str
    sub_category: Optional[str]
    emissions_source: Optional[str]
    unit: Optional[str]
    quantity: Optional[Decimal]
    conversion_factor: Optional[Decimal]
    energy_gj: Optional[Decimal]
    renewable_status: Optional[str]
    emissions_tco2e: Optional[Decimal]
    notes: Optional[str]
    quantity_each: Optional[Decimal]
    annual_kwh_per_unit: Optional[Decimal]
    reference_period_years: Optional[int]


class OrgEnergyDetailResponse(DashboardBase):
    rows: List[OrgEnergyDetailRow]


# ---------------------------------------------------------------------------
# Bind-params helper
# ---------------------------------------------------------------------------

def _bind(
    org_id: UUID,
    project_class: Optional[str] = None,
    program_name: Optional[str] = None,
    stage: Optional[str] = None,
    project_type_id: Optional[UUID] = None,
    project_typecast_id: Optional[UUID] = None,
    default_dataset_revision_id: Optional[UUID] = None,
) -> dict:
    return {
        "org_id": str(org_id),
        "project_class": project_class,
        "program_name": program_name,
        "stage": stage,
        "project_type_id": str(project_type_id) if project_type_id else None,
        "project_typecast_id": str(project_typecast_id) if project_typecast_id else None,
        "default_dataset_revision_id": str(default_dataset_revision_id) if default_dataset_revision_id else None,
        "project_option_id": None,
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


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

_ENERGY_SQL = text("""
WITH eligible_projects AS (
    -- All (project, stage_instance) pairs belonging to the given organisation,
    -- filtered by optional project_class, program_name, stage.
    -- Reference period per project: LEAST(operational_life_years, 50), default 50.
    SELECT DISTINCT
        p.id                                                        AS project_id,
        p.project_name                                              AS project_name,
        psi.id                                                      AS stage_instance_id,
        psi.stage::text                                             AS stage_type,
        LEAST(COALESCE(p.operational_life_years, 50), 50)           AS reference_period
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

all_rows AS (

    -- 1. bcDetailedLevel: Construction, Detailed Level (Grade 3), Fuels
    SELECT
        ad.id,
        ep.project_id,
        ep.project_name,
        ep.stage_type,
        'Construction'                                                           AS lifecycle_stage,
        'Detailed Level (Grade 3)'                                               AS input_table,
        ad.extra_fields->>'emissions_subcategory'                                AS sub_category,
        COALESCE(
            NULLIF(ad.extra_fields->>'emissions_source_name', ''),
            NULLIF(ad.extra_fields->>'emissions_source', '')
        )                                                                        AS emissions_source,
        ad.extra_fields->>'unit_code'                                            AS unit,
        ad.quantity                                                              AS quantity,
        NULL::text                                                               AS renewable_status,
        0::numeric AS emissions_tco2e,
        ad.extra_fields->>'notes'                                                AS notes,
        NULL::numeric                                                            AS quantity_each,
        NULL::numeric                                                            AS annual_kwh_per_unit,
        NULL::integer                                                            AS reference_period_years
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id         = ad.project_id
       AND ep.stage_instance_id  = ad.project_stage_instance_id
    WHERE ad.ui_table_key                         = 'bcDetailedLevel'
      AND ad.extra_fields->>'emissions_category'  = 'Fuels'
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

    UNION ALL

    -- 2. electricity: Construction, Electricity
    SELECT
        ad.id,
        ep.project_id,
        ep.project_name,
        ep.stage_type,
        'Construction'                                                           AS lifecycle_stage,
        'Electricity'                                                            AS input_table,
        'Electricity'                                                            AS sub_category,
        ad.extra_fields->>'emission_source'                                      AS emissions_source,
        'MWh'                                                                    AS unit,
        NULLIF(NULLIF(ad.extra_fields->>'quantity_mwh', ''), '-')::numeric       AS quantity,
        NULL::text                                                               AS renewable_status,
        0::numeric AS emissions_tco2e,
        ad.extra_fields->>'notes'                                                AS notes,
        NULL::numeric                                                            AS quantity_each,
        NULL::numeric                                                            AS annual_kwh_per_unit,
        NULL::integer                                                            AS reference_period_years
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id         = ad.project_id
       AND ep.stage_instance_id  = ad.project_stage_instance_id
    WHERE ad.ui_table_key = 'electricity'
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

    UNION ALL

    -- 3. replDetailed: In-use / Operations, Detailed Level (Grade 3), Fuels
    SELECT
        ad.id,
        ep.project_id,
        ep.project_name,
        ep.stage_type,
        'In-use / Operations'                                                    AS lifecycle_stage,
        'Detailed Level (Grade 3)'                                               AS input_table,
        ad.extra_fields->>'emissions_subcategory'                                AS sub_category,
        COALESCE(
            NULLIF(ad.extra_fields->>'emissions_source_name', ''),
            NULLIF(ad.extra_fields->>'emissions_source', '')
        )                                                                        AS emissions_source,
        ad.extra_fields->>'unit_code'                                            AS unit,
        ad.quantity                                                              AS quantity,
        NULL::text                                                               AS renewable_status,
        0::numeric AS emissions_tco2e,
        ad.extra_fields->>'notes'                                                AS notes,
        NULL::numeric                                                            AS quantity_each,
        NULL::numeric                                                            AS annual_kwh_per_unit,
        NULL::integer                                                            AS reference_period_years
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id         = ad.project_id
       AND ep.stage_instance_id  = ad.project_stage_instance_id
    WHERE ad.ui_table_key                        = 'replDetailed'
      AND ad.extra_fields->>'emissions_category' = 'Fuels'
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

    UNION ALL

    -- 4. opEnergy: In-use / Operations, Component Level (Grade 2)
    SELECT
        ad.id,
        ep.project_id,
        ep.project_name,
        ep.stage_type,
        'In-use / Operations'                                                    AS lifecycle_stage,
        'Component Level (Grade 2)'                                              AS input_table,
        ad.extra_fields->>'group_name'                                           AS sub_category,
        ad.extra_fields->>'item'                                                 AS emissions_source,
        'kWh'                                                                    AS unit,
        CASE
            WHEN oe.annual_kwh_per_unit IS NOT NULL
            THEN oe.annual_kwh_per_unit * COALESCE(ad.quantity, 0) * ep.reference_period
            ELSE NULL
        END                                                                      AS quantity,
        NULL::text                                                               AS renewable_status,
        0::numeric AS emissions_tco2e,
        ad.extra_fields->>'notes'                                                AS notes,
        ad.quantity                                                              AS quantity_each,
        oe.annual_kwh_per_unit                                                   AS annual_kwh_per_unit,
        ep.reference_period::integer                                             AS reference_period_years
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id         = ad.project_id
       AND ep.stage_instance_id  = ad.project_stage_instance_id
    LEFT JOIN LATERAL (
        SELECT (oe2.power_kw * oe2.hours_per_day * oe2.days_per_year)::numeric AS annual_kwh_per_unit
        FROM operational_equipment oe2
        WHERE oe2.id       = NULLIF(ad.extra_fields->>'eq_id', '')::uuid
          AND oe2.is_active = TRUE
        LIMIT 1
    ) oe ON TRUE
    WHERE ad.ui_table_key = 'opEnergy'
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

    UNION ALL

    -- 5. opEnergyDetailed: In-use / Operations, Detailed Level (Grade 3), Fuels
    SELECT
        ad.id,
        ep.project_id,
        ep.project_name,
        ep.stage_type,
        'In-use / Operations'                                                    AS lifecycle_stage,
        'Detailed Level (Grade 3)'                                               AS input_table,
        ad.extra_fields->>'emissions_subcategory'                                AS sub_category,
        COALESCE(
            NULLIF(ad.extra_fields->>'emissions_source_name', ''),
            NULLIF(ad.extra_fields->>'emissions_source', '')
        )                                                                        AS emissions_source,
        ad.extra_fields->>'unit_code'                                            AS unit,
        ad.quantity                                                              AS quantity,
        NULL::text                                                               AS renewable_status,
        0::numeric AS emissions_tco2e,
        ad.extra_fields->>'notes'                                                AS notes,
        NULL::numeric                                                            AS quantity_each,
        NULL::numeric                                                            AS annual_kwh_per_unit,
        NULL::integer                                                            AS reference_period_years
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id         = ad.project_id
       AND ep.stage_instance_id  = ad.project_stage_instance_id
    WHERE ad.ui_table_key                        = 'opEnergyDetailed'
      AND ad.extra_fields->>'emissions_category' = 'Fuels'
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

    UNION ALL

    -- 6. opEnergyElectricity: In-use / Operations, Electricity
    SELECT
        ad.id,
        ep.project_id,
        ep.project_name,
        ep.stage_type,
        'In-use / Operations'                                                    AS lifecycle_stage,
        'Electricity'                                                            AS input_table,
        'Electricity'                                                            AS sub_category,
        ad.extra_fields->>'emission_source'                                      AS emissions_source,
        'MWh'                                                                    AS unit,
        NULLIF(NULLIF(ad.extra_fields->>'quantity_mwh', ''), '-')::numeric       AS quantity,
        NULL::text                                                               AS renewable_status,
        0::numeric AS emissions_tco2e,
        ad.extra_fields->>'notes'                                                AS notes,
        NULL::numeric                                                            AS quantity_each,
        NULL::numeric                                                            AS annual_kwh_per_unit,
        NULL::integer                                                            AS reference_period_years
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id         = ad.project_id
       AND ep.stage_instance_id  = ad.project_stage_instance_id
    WHERE ad.ui_table_key = 'opEnergyElectricity'
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

),

with_conversions AS (
    SELECT
        r.id,
        r.project_id,
        r.project_name,
        r.stage_type,
        r.lifecycle_stage,
        r.input_table,
        r.sub_category,
        r.emissions_source,
        r.unit,
        r.quantity,
        COALESCE(rec.renewable_status, 'Non-renewable')                         AS renewable_status,
        r.emissions_tco2e,
        r.notes,
        r.quantity_each,
        r.annual_kwh_per_unit,
        r.reference_period_years,
        -- Conversion factor (GJ per input unit); NULL when unit is already 'GJ'
        CASE
            WHEN r.unit = 'GJ'                                 THEN NULL
            ELSE COALESCE(uc_view.conversion_factor, edc.energy_density)
        END                                                                      AS conversion_factor,
        -- Energy use (GJ)
        CASE
            WHEN r.unit = 'GJ'
                THEN r.quantity
            WHEN COALESCE(uc_view.conversion_factor, edc.energy_density) IS NOT NULL
                THEN r.quantity * COALESCE(uc_view.conversion_factor, edc.energy_density)
            ELSE NULL
        END                                                                      AS energy_gj
    FROM all_rows r
    -- Renewable status: looked up from v_renewable_energy_status view
    --                   Match on dataset_revision_id to get correct dataset
    LEFT JOIN v_renewable_energy_status rec
        ON rec.emissions_source = r.emissions_source
        AND rec.is_active = TRUE
        AND rec.dataset_revision_id = :default_dataset_revision_id
    -- Step 1: standard energy-unit conversion (e.g. MWh -> GJ = 3.6)
    --         Direct unit conversions (energy units) - not tied to fuel or dataset
    LEFT JOIN v_unit_conversions_to_gj uc_view
        ON uc_view.from_unit_code = r.unit
    -- Step 2: fuel energy density fallback (e.g. kL of Diesel oil -> GJ = 38.6)
    --         Lookup by fuel name only (emissions_source)
    --         Use ROW_NUMBER() to pick ONLY 1 row per fuel, prioritizing matching dataset_revision_id
    LEFT JOIN (
        SELECT name, energy_density, dataset_revision_id,
            ROW_NUMBER() OVER (
                PARTITION BY name
                ORDER BY (dataset_revision_id = :default_dataset_revision_id) DESC, dataset_revision_id DESC
            ) AS rn
        FROM energy_density_conversions
        WHERE is_active = TRUE
            AND (dataset_revision_id IS NULL OR dataset_revision_id = :default_dataset_revision_id)
    ) edc ON edc.name = r.emissions_source AND edc.rn = 1
    WHERE COALESCE(r.quantity, 0) > 0
)

SELECT
    id,
    project_id,
    project_name,
    stage_type,
    lifecycle_stage,
    input_table,
    sub_category,
    emissions_source,
    unit,
    quantity,
    conversion_factor,
    energy_gj,
    renewable_status,
    emissions_tco2e,
    notes,
    quantity_each,
    annual_kwh_per_unit,
    reference_period_years
FROM with_conversions
ORDER BY project_name, lifecycle_stage, input_table, sub_category, emissions_source
""")

_DEFAULT_DATASET_REVISION_SQL = text("""
SELECT id FROM dataset_revisions
WHERE scope_type = 'DEFAULT' AND status = 'published'
ORDER BY created_at DESC LIMIT 1
""")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

_TYPES = ("Non-renewable", "Renewable")


@router.get("/summary", response_model=OrgEnergySummaryResponse)
async def org_energy_summary(
    org_id: UUID = Query(..., description="Organisation UUID"),
    project_class: Optional[str] = Query(None),
    program_name: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    project_type_id: Optional[UUID] = Query(None, description="Filter by project type (benchmark mastertype UUID)"),
    project_typecast: Optional[UUID] = Query(None, description="Filter by project typecast UUID"),
    db: AsyncSession = Depends(get_session),
):
    """Returns org-level renewable energy summary in the same format as the project dashboard."""
    try:
        dr_result = await db.execute(_DEFAULT_DATASET_REVISION_SQL)
        default_dataset_revision_id = dr_result.scalar()
    except Exception:
        default_dataset_revision_id = None

    params = _bind(
        org_id,
        project_class=_normalize_project_class(project_class),
        program_name=program_name,
        stage=_normalize_stage(stage),
        project_type_id=project_type_id,
        project_typecast_id=project_typecast,
        default_dataset_revision_id=default_dataset_revision_id,
    )
    try:
        result = await db.execute(_ENERGY_SQL, params)
        rows = result.mappings().all()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Database query failed: {exc}") from exc

    # Aggregate GJ by (stage, renewable_status) and by (source, renewable_status, stage)
    agg: dict[tuple, Decimal] = {}
    fuel_agg: dict[tuple, Decimal] = {}

    for row in rows:
        gj = Decimal(str(row["energy_gj"])) if row["energy_gj"] is not None else Decimal("0")
        stage_label = row["lifecycle_stage"]
        rtype = row["renewable_status"] or "Non-renewable"
        source = row["emissions_source"] or "(unspecified)"
        agg[(stage_label, rtype)] = agg.get((stage_label, rtype), Decimal("0")) + gj
        fuel_agg[(source, rtype, stage_label)] = fuel_agg.get((source, rtype, stage_label), Decimal("0")) + gj

    # Stages that have any energy data
    all_stages = ["Construction", "In-use / Operations"]
    data_stages = [
        s for s in all_stages
        if sum(agg.get((s, t), Decimal("0")) for t in _TYPES) > Decimal("0")
    ]

    lifecycle_nr = sum(agg.get((s, "Non-renewable"), Decimal("0")) for s in data_stages)
    lifecycle_r  = sum(agg.get((s, "Renewable"),     Decimal("0")) for s in data_stages)
    lifecycle_total = lifecycle_nr + lifecycle_r

    abs_nr: dict[str, float] = {}
    abs_r:  dict[str, float] = {}
    pct_nr: dict[str, float] = {}
    pct_r:  dict[str, float] = {}

    for s in data_stages:
        nr = agg.get((s, "Non-renewable"), Decimal("0"))
        r  = agg.get((s, "Renewable"),     Decimal("0"))
        total = nr + r
        abs_nr[s] = round(float(nr), OUTPUT_DECIMAL_PLACES)
        abs_r[s]  = round(float(r),  OUTPUT_DECIMAL_PLACES)
        pct_nr[s] = round(float(nr / total * 100), OUTPUT_DECIMAL_PLACES) if total else 0.0
        pct_r[s]  = round(float(r  / total * 100), OUTPUT_DECIMAL_PLACES) if total else 0.0

    stages_for_response = list(data_stages)
    if len(data_stages) > 0:
        abs_nr["Lifecycle"] = round(float(lifecycle_nr), OUTPUT_DECIMAL_PLACES)
        abs_r["Lifecycle"]  = round(float(lifecycle_r),  OUTPUT_DECIMAL_PLACES)
        pct_nr["Lifecycle"] = round(float(lifecycle_nr / lifecycle_total * 100), OUTPUT_DECIMAL_PLACES) if lifecycle_total else 0.0
        pct_r["Lifecycle"]  = round(float(lifecycle_r  / lifecycle_total * 100), OUTPUT_DECIMAL_PLACES) if lifecycle_total else 0.0
        stages_for_response.append("Lifecycle")

    fuel_pairs = sorted(
        set((k[0], k[1]) for k in fuel_agg),
        key=lambda x: (x[1], x[0]),  # Non-renewable first, then alphabetical
    )
    by_fuel_source: list[OrgEnergyFuelByStage] = []
    for source, rtype in fuel_pairs:
        c_gj = fuel_agg.get((source, rtype, "Construction"),       Decimal("0"))
        i_gj = fuel_agg.get((source, rtype, "In-use / Operations"), Decimal("0"))
        l_gj = c_gj + i_gj
        by_fuel_source.append(
            OrgEnergyFuelByStage(
                emissions_source=source,
                renewable_status=rtype,
                construction_gj=c_gj,
                inuse_gj=i_gj,
                lifecycle_gj=l_gj,
                lifecycle_pct=(l_gj / lifecycle_total * 100) if lifecycle_total else Decimal("0"),
            )
        )

    return OrgEnergySummaryResponse(
        unit="GJ",
        stages=stages_for_response,
        absolute={"nonRenewable": abs_nr, "renewable": abs_r},
        percentage={"nonRenewable": pct_nr, "renewable": pct_r},
        by_fuel_source=by_fuel_source,
    )


@router.get("/detail", response_model=OrgEnergyDetailResponse)
async def org_energy_detail(
    org_id: UUID = Query(..., description="Organisation UUID"),
    project_class: Optional[str] = Query(None),
    program_name: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    project_type_id: Optional[UUID] = Query(None, description="Filter by project type (benchmark mastertype UUID)"),
    project_typecast: Optional[UUID] = Query(None, description="Filter by project typecast UUID"),
    db: AsyncSession = Depends(get_session),
):
    """Returns every individual energy row across all projects in the organisation."""
    try:
        dr_result = await db.execute(_DEFAULT_DATASET_REVISION_SQL)
        default_dataset_revision_id = dr_result.scalar()
    except Exception:
        default_dataset_revision_id = None

    params = _bind(
        org_id,
        project_class=_normalize_project_class(project_class),
        program_name=program_name,
        stage=_normalize_stage(stage),
        project_type_id=project_type_id,
        project_typecast_id=project_typecast,
        default_dataset_revision_id=default_dataset_revision_id,
    )
    try:
        result = await db.execute(_ENERGY_SQL, params)
        rows = result.mappings().all()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Database query failed: {exc}") from exc

    emissions_by_id = await emissions_totals_by_activity(db, (r["id"] for r in rows))
    return OrgEnergyDetailResponse(rows=[
        OrgEnergyDetailRow(**{**dict(r), "emissions_tco2e": emissions_by_id.get(r["id"], Decimal(0))})
        for r in rows
    ])

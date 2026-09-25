"""
routers/dashboard_energy.py

Dashboard Results API — Renewable Energy

Two endpoints:
  GET /api/dashboard/energy/summary  — chart/table data for the "Renewable Energy" dashboard screen
  GET /api/dashboard/energy/detail   — row-level detail for "View detailed results"

Sources (ui_table_key):
  bcDetailedLevel     → Construction,        Detailed Level (Grade 3),  category = 'Fuels'
  electricity         → Construction,        Electricity
  replDetailed        → In-use / Operations, Detailed Level (Grade 3),  category = 'Fuels'
  opEnergy            → In-use / Operations, Component Level (Grade 2)
  opEnergyDetailed    → In-use / Operations, Detailed Level (Grade 3),  category = 'Fuels'
  opEnergyElectricity → In-use / Operations, Electricity

Energy quantities are converted to GJ using:
  1. unit_conversions          (e.g. MWh × 3.6 = GJ, kWh × 0.0036 = GJ)
  2. energy_density_conversions (fallback for physical units — matches by fuel name AND unit)
  3. If unit is already 'GJ', no conversion needed

opEnergy (Component Level Grade 2) quantity (MWh) is derived as:
  power_kw × hours_per_day × days_per_year / 1000  [per unit, per year]
  × quantity (each count)
  × reference_period (= MIN(ops_end - ops_start, 50) from project context)

Renewable status is looked up from the `renewable_energy_classifications` DB table
  (the backend equivalent of Excel Table61).  Matched on emissions_source (case-sensitive).
  Falls back to 'Non-renewable' when no matching row is found (is_active = TRUE).

Query params
------------
  project_id        UUID  required
  stage_instance_id UUID  required
"""

from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from services._calc_utils import DashboardBase, OUTPUT_DECIMAL_PLACES
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from services.project_context_helper import ProjectContextHelper

router = APIRouter(
    prefix="/api/dashboard/energy",
    tags=["Dashboard - Renewable Energy"],
)

# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class EnergyFuelByStage(DashboardBase):
    """Energy breakdown by individual source — used in the fuel-source detail table."""

    emissions_source: str
    renewable_status: str
    construction_gj: Decimal
    inuse_gj: Decimal
    lifecycle_gj: Decimal
    lifecycle_pct: Decimal


class EnergySummaryResponse(DashboardBase):
    """
    Aggregated datasets for the Renewable Energy dashboard screen.

    by_source_table  → 'Renewable energy consumption by source' table (Renewable / Non-renewable × stage)
    chart_data       → 'Renewable energy usage by stage (%)' bar chart
    by_fuel_source   → 'Energy breakdown by source' table (per individual energy source)
    """

    # Shape matches RenewableEnergyTab.tsx:
    #   { unit, stages, absolute: {nonRenewable, renewable}, percentage: {nonRenewable, renewable} }
    unit: str                                        # always "GJ"
    stages: List[str]                                # ordered list of stage labels that have data
    absolute: dict                                   # {nonRenewable: {stage: gj}, renewable: {stage: gj}}
    percentage: dict                                 # {nonRenewable: {stage: pct}, renewable: {stage: pct}}
    by_fuel_source: List[EnergyFuelByStage]          # per-source breakdown (extra, not rendered by tab)


class EnergyDetailRow(DashboardBase):
    """One row for the 'View detailed results' page."""

    id: UUID
    lifecycle_stage: str
    input_table: str
    sub_category: Optional[str]
    emissions_source: Optional[str]
    unit: Optional[str]
    quantity: Optional[Decimal]
    conversion_factor: Optional[Decimal]   # GJ per input unit; NULL when unit is already GJ
    energy_gj: Optional[Decimal]
    renewable_status: str
    emissions_tco2e: Optional[Decimal]
    notes: Optional[str]
    # opEnergy interim audit columns — NULL for all other sources
    # Auditors can verify: annual_kwh_per_unit × quantity_each × reference_period_years = quantity (total kWh)
    quantity_each: Optional[Decimal]        # raw 'Each' count from user input
    annual_kwh_per_unit: Optional[Decimal]  # kWh/year per unit from operational_equipment
    reference_period_years: Optional[int]   # project reference period (years, capped at 50)


class EnergyDetailResponse(DashboardBase):
    rows: List[EnergyDetailRow]


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

_ENERGY_ROWS_SQL = text("""
WITH all_rows AS (

    -- 1. bcDetailedLevel: Construction, Detailed Level (Grade 3), Fuels
    SELECT
        ad.id,
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
        NULLIF(NULLIF(ad.extra_fields->>'total_emissions_tco2e', ''), '-')::numeric           AS emissions_tco2e,
        ad.extra_fields->>'notes'                                                AS notes,
        NULL::numeric                                                            AS quantity_each,
        NULL::numeric                                                            AS annual_kwh_per_unit,
        NULL::integer                                                            AS reference_period_years
    FROM activity_data ad
    WHERE ad.project_id                              = :project_id
      AND ad.project_stage_instance_id               = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND ad.ui_table_key                            = 'bcDetailedLevel'
      AND ad.extra_fields->>'emissions_category'     = 'Fuels'

    UNION ALL

    -- 2. electricity: Construction, Electricity
    SELECT
        ad.id,
        'Construction'                                                           AS lifecycle_stage,
        'Electricity'                                                            AS input_table,
        'Electricity'                                                            AS sub_category,
        ad.extra_fields->>'emission_source'                                      AS emissions_source,
        'MWh'                                                                    AS unit,
        NULLIF(NULLIF(ad.extra_fields->>'quantity_mwh', ''), '-')::numeric                    AS quantity,
        NULL::text                                                               AS renewable_status,
        NULLIF(NULLIF(ad.extra_fields->>'total_emissions_tco2e', ''), '-')::numeric           AS emissions_tco2e,
        ad.extra_fields->>'notes'                                                AS notes,
        NULL::numeric                                                            AS quantity_each,
        NULL::numeric                                                            AS annual_kwh_per_unit,
        NULL::integer                                                            AS reference_period_years
    FROM activity_data ad
    WHERE ad.project_id                              = :project_id
      AND ad.project_stage_instance_id               = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND ad.ui_table_key                            = 'electricity'

    UNION ALL

    -- 3. replDetailed: In-use / Operations, Detailed Level (Grade 3), Fuels
    SELECT
        ad.id,
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
        NULLIF(NULLIF(ad.extra_fields->>'total_emissions_tco2e', ''), '-')::numeric           AS emissions_tco2e,
        ad.extra_fields->>'notes'                                                AS notes,
        NULL::numeric                                                            AS quantity_each,
        NULL::numeric                                                            AS annual_kwh_per_unit,
        NULL::integer                                                            AS reference_period_years
    FROM activity_data ad
    WHERE ad.project_id                              = :project_id
      AND ad.project_stage_instance_id               = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND ad.ui_table_key                            = 'replDetailed'
      AND ad.extra_fields->>'emissions_category'     = 'Fuels'

    UNION ALL

    -- 4. opEnergy: In-use / Operations, Component Level (Grade 2)
    --    quantity (kWh) = power_kw * hours_per_day * days_per_year  [kWh/year per unit]
    --                     * each_count * reference_period
    --    GJ conversion applied via unit_conversions (kWh -> GJ = 0.0036)
    SELECT
        ad.id,
        'In-use / Operations'                                                    AS lifecycle_stage,
        'Component Level (Grade 2)'                                              AS input_table,
        ad.extra_fields->>'group_name'                                           AS sub_category,
        ad.extra_fields->>'item'                                                 AS emissions_source,
        'kWh'                                                                    AS unit,
        CASE
            WHEN oe.annual_kwh_per_unit IS NOT NULL
            THEN oe.annual_kwh_per_unit * COALESCE(ad.quantity, 0) * CAST(:reference_period AS numeric)
            ELSE NULL
        END                                                                      AS quantity,
        NULL::text                                                               AS renewable_status,
        NULLIF(NULLIF(ad.extra_fields->>'total_emissions_tco2e', ''), '-')::numeric           AS emissions_tco2e,
        ad.extra_fields->>'notes'                                                AS notes,
        ad.quantity                                                              AS quantity_each,
        oe.annual_kwh_per_unit                                                   AS annual_kwh_per_unit,
        CAST(:reference_period AS integer)                                        AS reference_period_years
    FROM activity_data ad
    LEFT JOIN LATERAL (
        SELECT (oe2.power_kw * oe2.hours_per_day * oe2.days_per_year)::numeric
            AS annual_kwh_per_unit
        FROM operational_equipment oe2
        WHERE oe2.id       = NULLIF(ad.extra_fields->>'eq_id', '')::uuid
          AND oe2.is_active = TRUE
        LIMIT 1
    ) oe ON TRUE
    WHERE ad.project_id                              = :project_id
      AND ad.project_stage_instance_id               = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND ad.ui_table_key                            = 'opEnergy'

    UNION ALL

    -- 5. opEnergyDetailed: In-use / Operations, Detailed Level (Grade 3), Fuels
    SELECT
        ad.id,
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
        NULLIF(NULLIF(ad.extra_fields->>'total_emissions_tco2e', ''), '-')::numeric           AS emissions_tco2e,
        ad.extra_fields->>'notes'                                                AS notes,
        NULL::numeric                                                            AS quantity_each,
        NULL::numeric                                                            AS annual_kwh_per_unit,
        NULL::integer                                                            AS reference_period_years
    FROM activity_data ad
    WHERE ad.project_id                              = :project_id
      AND ad.project_stage_instance_id               = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND ad.ui_table_key                            = 'opEnergyDetailed'
      AND ad.extra_fields->>'emissions_category'     = 'Fuels'

    UNION ALL

    -- 6. opEnergyElectricity: In-use / Operations, Electricity
    SELECT
        ad.id,
        'In-use / Operations'                                                    AS lifecycle_stage,
        'Electricity'                                                            AS input_table,
        'Electricity'                                                            AS sub_category,
        ad.extra_fields->>'emission_source'                                      AS emissions_source,
        'MWh'                                                                    AS unit,
        NULLIF(NULLIF(ad.extra_fields->>'quantity_mwh', ''), '-')::numeric                    AS quantity,
        NULL::text                                                               AS renewable_status,
        NULLIF(NULLIF(ad.extra_fields->>'total_emissions_tco2e', ''), '-')::numeric           AS emissions_tco2e,
        ad.extra_fields->>'notes'                                                AS notes,
        NULL::numeric                                                            AS quantity_each,
        NULL::numeric                                                            AS annual_kwh_per_unit,
        NULL::integer                                                            AS reference_period_years
    FROM activity_data ad
    WHERE ad.project_id                              = :project_id
      AND ad.project_stage_instance_id               = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND ad.ui_table_key                            = 'opEnergyElectricity'

),

with_conversions AS (
    SELECT
        r.id,
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
    -- Step 1: standard energy-unit conversion (e.g. MWh → GJ = 3.6)
    --         Direct unit conversions (energy units) — not tied to fuel or dataset
    LEFT JOIN v_unit_conversions_to_gj uc_view
        ON uc_view.from_unit_code = r.unit
    -- Step 2: fuel energy density fallback (e.g. kL of Diesel oil → GJ = 38.6)
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
ORDER BY lifecycle_stage, input_table, sub_category, emissions_source
""")

# Lookup the stage type (CONSTRUCTION / RECURRING / etc.) for a stage instance
_STAGE_TYPE_SQL = text("""
SELECT stage FROM project_stage_instances WHERE id = :stage_instance_id
""")

# Get the default dataset revision ID
_DEFAULT_DATASET_REVISION_SQL = text("""
SELECT id FROM dataset_revisions 
WHERE scope_type = 'DEFAULT' AND status = 'published'
ORDER BY created_at DESC LIMIT 1
""")


def _bind(
    project_id: UUID,
    stage_instance_id: UUID,
    reference_period: int,
    default_dataset_revision_id: Optional[UUID] = None,
    project_option_id: Optional[UUID] = None,
    submission_period_id: Optional[UUID] = None,
) -> dict:
    return {
        "project_id": str(project_id),
        "stage_instance_id": str(stage_instance_id),
        "reference_period": reference_period,
        "default_dataset_revision_id": str(default_dataset_revision_id) if default_dataset_revision_id else None,
        "project_option_id": str(project_option_id) if project_option_id else None,
        "submission_period_id": str(submission_period_id) if submission_period_id else None,
    }


def _calc_reference_period(ctx: dict) -> int:
    """Derive opEnergy reference period (years) from project context."""
    ops_start = ctx.get("operations_start_year")
    ops_end = ctx.get("operations_end_year")
    if ops_start is not None and ops_end is not None and ops_end > ops_start:
        return min(ops_end - ops_start, 50)
    return 50


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

_TYPES = ("Non-renewable", "Renewable")


@router.get(
    "/summary",
    response_model=EnergySummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Renewable energy summary — by-source table and stage chart",
    description=(
        "Returns aggregated renewable energy data for the dashboard:\n\n"
        "- **by_source_table** — energy (GJ) and % split by Renewable / Non-renewable "
        "× lifecycle stage (Construction, In-use / Operations, Lifecycle)\n"
        "- **chart_data** — data points for the 'Renewable energy usage by stage (%)' bar chart\n\n"
        "opEnergy (Component Level Grade 2) quantities are derived from equipment power × "
        "hours × days × count × reference period."
    ),
)
async def get_energy_summary(
    project_id: UUID = Query(..., description="Project UUID"),
    stage_instance_id: UUID = Query(..., description="Stage instance UUID"),
    project_option_id: Optional[UUID] = Query(None, description="Project option UUID (optional filter)"),
    submission_period_id: Optional[UUID] = Query(None, description="Submission period UUID (optional filter)"),
    db: AsyncSession = Depends(get_session),
) -> EnergySummaryResponse:
    ctx = await ProjectContextHelper.get_project_context(db, project_id)
    reference_period = _calc_reference_period(ctx)
    
    # Get default dataset revision ID
    try:
        dr_result = await db.execute(_DEFAULT_DATASET_REVISION_SQL)
        default_dataset_revision_id = dr_result.scalar()
    except Exception:
        default_dataset_revision_id = None
    
    params = _bind(project_id, stage_instance_id, reference_period, default_dataset_revision_id, project_option_id, submission_period_id)

    # Determine whether this is a RECURRING stage instance so we can rename the
    # "In-use / Operations" label to "Recurring project" to match the frontend.
    try:
        st_result = await db.execute(
            _STAGE_TYPE_SQL, {"stage_instance_id": str(stage_instance_id)}
        )
        stage_type = (st_result.scalar() or "CONSTRUCTION").upper()
    except Exception:
        stage_type = "CONSTRUCTION"

    is_recurring = (stage_type == "RECURRING")

    try:
        result = await db.execute(_ENERGY_ROWS_SQL, params)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {exc}",
        )

    rows = result.mappings().all()

    # Remap "In-use / Operations" → "Recurring project" for recurring stages
    def _stage_label(raw: str) -> str:
        if is_recurring and raw == "In-use / Operations":
            return "Recurring project"
        return raw

    # ── Aggregate GJ by (stage_label, renewable_status) ─────────────────────
    agg: dict[tuple, Decimal] = {}
    # ── Aggregate GJ by (emissions_source, renewable_status, stage_label) ────
    fuel_agg: dict[tuple, Decimal] = {}

    for row in rows:
        gj = Decimal(str(row["energy_gj"])) if row["energy_gj"] is not None else Decimal("0")
        stage = _stage_label(row["lifecycle_stage"])
        rtype = row["renewable_status"]
        source = row["emissions_source"] or "(unspecified)"
        agg[(stage, rtype)] = agg.get((stage, rtype), Decimal("0")) + gj
        fuel_agg[(source, rtype, stage)] = fuel_agg.get((source, rtype, stage), Decimal("0")) + gj

    # ── Determine which data stages have any GJ ───────────────────────────────
    data_stages = [s for s in (
        ["Recurring project"] if is_recurring else ["Construction", "In-use / Operations"]
    ) if sum(agg.get((s, t), Decimal("0")) for t in _TYPES) > Decimal("0")]

    # Lifecycle = sum across all data stages (only for non-recurring projects)
    lifecycle_nr = sum(agg.get((s, "Non-renewable"), Decimal("0")) for s in data_stages)
    lifecycle_r  = sum(agg.get((s, "Renewable"),     Decimal("0")) for s in data_stages)
    lifecycle_total = lifecycle_nr + lifecycle_r

    # ── Build absolute / percentage dicts ────────────────────────────────────
    abs_nr: dict[str, float] = {}
    abs_r:  dict[str, float] = {}
    pct_nr: dict[str, float] = {}
    pct_r:  dict[str, float] = {}

    for stage in data_stages:
        nr = agg.get((stage, "Non-renewable"), Decimal("0"))
        r  = agg.get((stage, "Renewable"),     Decimal("0"))
        total = nr + r
        abs_nr[stage] = round(float(nr), OUTPUT_DECIMAL_PLACES)
        abs_r[stage]  = round(float(r), OUTPUT_DECIMAL_PLACES)
        pct_nr[stage] = round(float(nr / total * 100), OUTPUT_DECIMAL_PLACES) if total else 0.0
        pct_r[stage]  = round(float(r  / total * 100), OUTPUT_DECIMAL_PLACES) if total else 0.0

    # Add "Lifecycle" stage (non-recurring only) if there is more than one data stage
    stages_for_response = list(data_stages)
    if not is_recurring and len(data_stages) > 0:
        abs_nr["Lifecycle"] = round(float(lifecycle_nr), OUTPUT_DECIMAL_PLACES)
        abs_r["Lifecycle"]  = round(float(lifecycle_r), OUTPUT_DECIMAL_PLACES)
        pct_nr["Lifecycle"] = round(float(lifecycle_nr / lifecycle_total * 100), OUTPUT_DECIMAL_PLACES) if lifecycle_total else 0.0
        pct_r["Lifecycle"]  = round(float(lifecycle_r  / lifecycle_total * 100), OUTPUT_DECIMAL_PLACES) if lifecycle_total else 0.0
        stages_for_response.append("Lifecycle")

    # ── Build by_fuel_source ─────────────────────────────────────────────────
    fuel_pairs = sorted(
        set((k[0], k[1]) for k in fuel_agg),
        key=lambda x: (x[1], x[0]),  # Non-renewable first, then alphabetical
    )
    by_fuel_source: list[EnergyFuelByStage] = []
    for source, rtype in fuel_pairs:
        c_gj = fuel_agg.get((source, rtype, "Construction"), Decimal("0"))
        i_gj = fuel_agg.get(
            (source, rtype, "Recurring project" if is_recurring else "In-use / Operations"),
            Decimal("0"),
        )
        l_gj = c_gj + i_gj
        by_fuel_source.append(
            EnergyFuelByStage(
                emissions_source=source,
                renewable_status=rtype,
                construction_gj=c_gj,
                inuse_gj=i_gj,
                lifecycle_gj=l_gj,
                lifecycle_pct=(l_gj / lifecycle_total * 100) if lifecycle_total else Decimal("0"),
            )
        )

    return EnergySummaryResponse(
        unit="GJ",
        stages=stages_for_response,
        absolute={"nonRenewable": abs_nr, "renewable": abs_r},
        percentage={"nonRenewable": pct_nr, "renewable": pct_r},
        by_fuel_source=by_fuel_source,
    )


@router.get(
    "/detail",
    response_model=EnergyDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Renewable energy detail — row-level data for 'View detailed results'",
    description=(
        "Returns a flat list of energy rows for the 'View detailed results' page.\n\n"
        "Columns: Lifecycle Stage | Input Table | Sub-category | Emissions Source | Unit | "
        "Quantity | Conversion Factor (GJ/unit) | Energy Use (GJ) | Renewable Status | "
        "Emissions (tCO2e) | Notes\n\n"
        "Sources: bcDetailedLevel, electricity, replDetailed, opEnergy, "
        "opEnergyDetailed, opEnergyElectricity."
    ),
)
async def get_energy_detail(
    project_id: UUID = Query(..., description="Project UUID"),
    stage_instance_id: UUID = Query(..., description="Stage instance UUID"),
    project_option_id: Optional[UUID] = Query(None, description="Project option UUID (optional filter)"),
    submission_period_id: Optional[UUID] = Query(None, description="Submission period UUID (optional filter)"),
    db: AsyncSession = Depends(get_session),
) -> EnergyDetailResponse:
    ctx = await ProjectContextHelper.get_project_context(db, project_id)
    reference_period = _calc_reference_period(ctx)
    
    # Get default dataset revision ID
    try:
        dr_result = await db.execute(_DEFAULT_DATASET_REVISION_SQL)
        default_dataset_revision_id = dr_result.scalar()
    except Exception:
        default_dataset_revision_id = None
    
    params = _bind(project_id, stage_instance_id, reference_period, default_dataset_revision_id, project_option_id, submission_period_id)

    try:
        result = await db.execute(_ENERGY_ROWS_SQL, params)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {exc}",
        )

    rows = [
        EnergyDetailRow(
            id=r["id"],
            lifecycle_stage=r["lifecycle_stage"],
            input_table=r["input_table"],
            sub_category=r["sub_category"],
            emissions_source=r["emissions_source"],
            unit=r["unit"],
            quantity=r["quantity"],
            conversion_factor=r["conversion_factor"],
            energy_gj=r["energy_gj"],
            renewable_status=r["renewable_status"],
            emissions_tco2e=r["emissions_tco2e"],
            notes=r["notes"],
            quantity_each=r["quantity_each"],
            annual_kwh_per_unit=r["annual_kwh_per_unit"],
            reference_period_years=r["reference_period_years"],
        )
        for r in result.mappings().all()
    ]

    return EnergyDetailResponse(rows=rows)

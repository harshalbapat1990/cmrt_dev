"""
routers/dashboard_carbon_valuation.py

Dashboard Results API - Carbon Valuation (Detailed table)

Returns the detailed yearly carbon valuation table with the same logical
structure as the Excel "Detailed tables: Carbon valuation" section, plus the
construction/operations electricity detail tables used in the yearly splits.
"""

from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from services._calc_utils import DashboardBase
from services.project_context_helper import ProjectContextHelper
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from routers.dashboard_emissions_breakdown import _MODULE_SQL


router = APIRouter(
    prefix="/api/dashboard/carbon-valuation",
    tags=["Dashboard - Carbon Valuation"],
)


_MAX_REFERENCE_PERIOD = 50


def _dec(val) -> Decimal:
    if val is None:
        return Decimal(0)
    return Decimal(str(val))


class CarbonValuationYearRow(DashboardBase):
    year: int
    upfrontA1A5: Decimal
    useB1: Decimal
    maintenanceRepairReplacementRefurbishmentB2B5: Decimal
    operationalEnergyWaterB6B7: Decimal
    usersB8: Decimal
    totalEmissionsA1B8: Decimal
    centralCarbonValuePerTco2e: Decimal
    centralCarbonValue: Decimal
    lowCarbonValuePerTco2e: Decimal
    lowCarbonValue: Decimal
    highCarbonValuePerTco2e: Decimal
    highCarbonValue: Decimal


class CarbonValuationDetailResponse(DashboardBase):
    rows: List[CarbonValuationYearRow]


_PROJECT_DATES_SQL = text(
    """
    SELECT
        construction_start_date,
        construction_end_date,
        commencement_of_operations,
        operational_life_years
    FROM project
    WHERE id = CAST(:project_id AS uuid)
    """
)


_ELEC_BY_YEAR_SQL = text(
    """
    SELECT
        COALESCE(
            NULLIF(NULLIF(ad.extra_fields->>'year', ''), '-')::int,
            NULLIF(NULLIF(ad.extra_fields->>'assessment_year', ''), '-')::int
        ) AS assessment_year,
        SUM(CASE WHEN er.accounting_basis = 'location' THEN er.value ELSE 0 END) AS location_based_tco2e,
        SUM(CASE WHEN er.accounting_basis = 'market' THEN er.value ELSE 0 END) AS market_based_tco2e
    FROM activity_data ad
    JOIN emissions_results er ON er.activity_data_id = ad.id
    WHERE ad.project_id = CAST(:project_id AS uuid)
      AND ad.project_stage_instance_id = CAST(:stage_instance_id AS uuid)
      AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND ad.ui_table_key = :ui_table_key
      AND er.reporting_measure = 'actual'
      AND er.is_supplementary IS FALSE
      AND er.accounting_basis IN ('location', 'market')
    GROUP BY 1
    """
)


_B8_BY_YEAR_SQL = text(
    """
    SELECT
        COALESCE(
            NULLIF(NULLIF(ad.extra_fields->>'assessment_year', ''), '-')::int,
            NULLIF(NULLIF(ad.extra_fields->>'year', ''), '-')::int
        ) AS assessment_year,
        SUM(er.value) AS emissions_tco2e
    FROM activity_data ad
    JOIN emissions_results er ON er.activity_data_id = ad.id
    WHERE ad.project_id = CAST(:project_id AS uuid)
      AND ad.project_stage_instance_id = CAST(:stage_instance_id AS uuid)
      AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND ad.ui_table_key IN (
        'roadUsers', 'railUsers',
        'largeRoadUsers', 'largeRoadParams', 'largeRailUsers'
      )
      AND er.lifecycle_module_code = 'B8'
      AND er.reporting_measure = 'actual'
      AND er.is_supplementary IS FALSE
      AND er.accounting_basis IN ('common', 'location')
    GROUP BY 1
    """
)


_CARBON_PRICE_BY_YEAR_SQL = text(
    """
    SELECT DISTINCT ON (cv.range_code, cv.year)
        cv.range_code,
        cv.year,
        cv.value,
        COALESCE(cv.currency, '') AS currency
    FROM carbon_values cv
    JOIN jurisdictions j ON j.id = cv.jurisdiction_id
    JOIN dataset_revisions dr ON dr.id = cv.dataset_revision_id
    WHERE j.name = :jurisdiction
      AND cv.year BETWEEN :year_start AND :year_end
    ORDER BY cv.range_code, cv.year, dr.created_at DESC
    """
)


@router.get(
    "/details",
    response_model=CarbonValuationDetailResponse,
    summary="Carbon valuation detailed yearly table",
)
async def get_carbon_valuation_details(
    project_id: UUID = Query(..., description="Project UUID"),
    stage_instance_id: UUID = Query(..., description="Project stage instance UUID"),
    elec_method: str = Query("location", description="Electricity accounting: 'location' or 'market'"),
    project_option_id: Optional[UUID] = Query(None, description="Project option UUID (optional filter)"),
    submission_period_id: Optional[UUID] = Query(None, description="Submission period UUID (optional filter)"),
    db: AsyncSession = Depends(get_session),
) -> CarbonValuationDetailResponse:
    if elec_method not in ("location", "market"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="elec_method must be 'location' or 'market'",
        )

    pid = str(project_id)
    sid = str(stage_instance_id)
    oid = str(project_option_id) if project_option_id else None
    spid = str(submission_period_id) if submission_period_id else None

    project = await ProjectContextHelper.fetch_project(db, project_id)
    jurisdiction = await ProjectContextHelper.fetch_jurisdiction(db, project_id)

    date_result = await db.execute(_PROJECT_DATES_SQL, {"project_id": pid})
    date_row = date_result.mappings().fetchone()
    if date_row is None:
        raise HTTPException(status_code=404, detail="Project not found")

    if date_row["construction_start_date"] is None:
        raise HTTPException(status_code=422, detail="Project missing construction_start_date")
    if date_row["construction_end_date"] is None:
        raise HTTPException(status_code=422, detail="Project missing construction_end_date")
    if project.commencement_of_operations is None:
        raise HTTPException(status_code=422, detail="Project missing commencement_of_operations")
    if project.operational_life_years is None:
        raise HTTPException(status_code=422, detail="Project missing operational_life_years")

    construction_start_year = date_row["construction_start_date"].year
    construction_end_year = date_row["construction_end_date"].year
    operations_start_year = project.commencement_of_operations.year

    construction_years = max(1, construction_end_year - construction_start_year + 1)
    reference_period_years = max(1, min(int(project.operational_life_years), _MAX_REFERENCE_PERIOD))
    reference_period_end_year = operations_start_year + reference_period_years
    year_start = construction_start_year
    year_end = reference_period_end_year

    module_result = await db.execute(
        _MODULE_SQL,
        {
            "project_id": pid,
            "stage_instance_id": sid,
            "elec_method": elec_method,
            "jurisdiction": jurisdiction,
            "project_option_id": oid,
            "submission_period_id": spid,
        },
    )
    module_row = module_result.mappings().fetchone() or {}

    a1_a3 = _dec(module_row.get("a1_a3"))
    a4 = _dec(module_row.get("a4"))
    a5 = _dec(module_row.get("a5"))
    b1_total = _dec(module_row.get("b1"))
    b2_b5_total = _dec(module_row.get("b2_b5"))
    b6_total = _dec(module_row.get("b6"))
    b7_total = _dec(module_row.get("b7"))
    b8_total = _dec(module_row.get("b8"))

    async def _fetch_electricity_by_year(ui_table_key: str) -> Dict[int, Decimal]:
        rs = await db.execute(
            _ELEC_BY_YEAR_SQL,
            {"project_id": pid, "stage_instance_id": sid, "ui_table_key": ui_table_key,
             "project_option_id": oid, "submission_period_id": spid},
        )
        col = "market_based_tco2e" if elec_method == "market" else "location_based_tco2e"
        return {
            int(r["assessment_year"]): _dec(r[col])
            for r in rs.mappings().fetchall()
            if r["assessment_year"] is not None
        }

    async def _fetch_electricity_total(ui_table_key: str) -> Decimal:
        by_year = await _fetch_electricity_by_year(ui_table_key)
        return sum(by_year.values(), Decimal(0))

    construction_elec_by_year = await _fetch_electricity_by_year("electricity")
    operations_elec_by_year = await _fetch_electricity_by_year("opEnergyElectricity")
    construction_electricity_total = sum(construction_elec_by_year.values(), Decimal(0))
    operations_electricity_total = sum(operations_elec_by_year.values(), Decimal(0))

    upfront_total_a1_a5 = a1_a3 + a4 + a5
    upfront_excl_electricity = upfront_total_a1_a5 - construction_electricity_total
    b6_b7_total = b6_total + b7_total
    b6_b7_excl_electricity = b6_b7_total - operations_electricity_total

    b8_by_year_result = await db.execute(
        _B8_BY_YEAR_SQL,
        {
            "project_id": pid,
            "stage_instance_id": sid,
            "project_option_id": oid,
            "submission_period_id": spid,
        },
    )
    b8_year_map: Dict[int, Decimal] = {}
    for r in b8_by_year_result.mappings().fetchall():
        if r["assessment_year"] is None:
            continue
        b8_year_map[int(r["assessment_year"])] = _dec(r["emissions_tco2e"])

    if not b8_year_map and b8_total != 0:
        annual_b8 = b8_total / Decimal(reference_period_years)
        for yr in range(operations_start_year, reference_period_end_year + 1):
            b8_year_map[yr] = annual_b8

    prices_result = await db.execute(
        _CARBON_PRICE_BY_YEAR_SQL,
        {
            "jurisdiction": jurisdiction,
            "year_start": year_start,
            "year_end": year_end,
        },
    )
    price_lookup: Dict[str, Dict[int, Decimal]] = {
        "central": {},
        "low": {},
        "high": {},
    }
    for r in prices_result.mappings().fetchall():
        rc = (r["range_code"] or "").lower()
        if rc in price_lookup:
            price_lookup[rc][int(r["year"])] = _dec(r["value"])

    annual_b1 = b1_total / Decimal(reference_period_years)
    annual_b2_b5 = b2_b5_total / Decimal(reference_period_years)
    annual_b6_b7_non_elec = b6_b7_excl_electricity / Decimal(reference_period_years)
    annual_upfront_excl_elec = upfront_excl_electricity / Decimal(construction_years)

    rows: List[CarbonValuationYearRow] = []
    for year in range(year_start, year_end + 1):
        in_construction = construction_start_year <= year <= construction_end_year
        in_operations = year >= operations_start_year

        upfront = Decimal(0)
        if in_construction:
            upfront = annual_upfront_excl_elec + construction_elec_by_year.get(year, Decimal(0))

        use_b1 = annual_b1 if in_operations else Decimal(0)
        b2_b5 = annual_b2_b5 if in_operations else Decimal(0)
        b6_b7 = Decimal(0)
        if in_operations:
            b6_b7 = annual_b6_b7_non_elec + operations_elec_by_year.get(year, Decimal(0))
        users_b8 = b8_year_map.get(year, Decimal(0)) if in_operations else Decimal(0)

        total = upfront + use_b1 + b2_b5 + b6_b7 + users_b8
        central_per = price_lookup["central"].get(year, Decimal(0))
        low_per = price_lookup["low"].get(year, Decimal(0))
        high_per = price_lookup["high"].get(year, Decimal(0))

        rows.append(
            CarbonValuationYearRow(
                year=year,
                upfrontA1A5=upfront,
                useB1=use_b1,
                maintenanceRepairReplacementRefurbishmentB2B5=b2_b5,
                operationalEnergyWaterB6B7=b6_b7,
                usersB8=users_b8,
                totalEmissionsA1B8=total,
                centralCarbonValuePerTco2e=central_per,
                centralCarbonValue=total * central_per,
                lowCarbonValuePerTco2e=low_per,
                lowCarbonValue=total * low_per,
                highCarbonValuePerTco2e=high_per,
                highCarbonValue=total * high_per,
            )
        )

    return CarbonValuationDetailResponse(rows=rows)

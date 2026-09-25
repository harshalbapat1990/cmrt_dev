"""Organisational dashboard carbon valuation aggregated to yearly rows."""

from decimal import Decimal
import re
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from services._calc_utils import DashboardBase
from routers.dashboard_carbon_valuation import (
    _B8_BY_YEAR_SQL,
    _CARBON_PRICE_BY_YEAR_SQL,
    _ELEC_BY_YEAR_SQL,
    _MAX_REFERENCE_PERIOD,
    _dec,
)
from routers.dashboard_emissions_breakdown import _MODULE_SQL
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session

router = APIRouter(
    prefix="/api/org-dashboard/carbon-valuation",
    tags=["Org Dashboard - Carbon Valuation"],
)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class OrgCarbonValuationDetailRow(DashboardBase):
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


class OrgCarbonValuationTotals(DashboardBase):
    total_gross_emissions_tco2e: Decimal
    total_central_carbon_value: Decimal
    total_low_carbon_value: Decimal
    total_high_carbon_value: Decimal


class OrgCarbonValuationDetailResponse(DashboardBase):
    rows: List[OrgCarbonValuationDetailRow]
    totals: OrgCarbonValuationTotals


# ---------------------------------------------------------------------------
# Bind-params helper
# ---------------------------------------------------------------------------

def _bind(
    org_id: UUID,
    project_class: Optional[str] = None,
    program_name: Optional[str] = None,
    stage: Optional[str] = None,
    elec_method: str = "location",
    project_type_id: Optional[UUID] = None,
    project_typecast_id: Optional[UUID] = None,
) -> dict:
    return {
        "org_id": str(org_id),
        "project_class": project_class,
        "program_name": program_name,
        "stage": stage,
        "elec_method": elec_method,
        "project_type_id": str(project_type_id) if project_type_id else None,
        "project_typecast_id": str(project_typecast_id) if project_typecast_id else None,
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

_ELIGIBLE_PROJECTS_SQL = text("""
SELECT
    p.id AS project_id,
    p.project_name AS project_name,
    psi.id AS stage_instance_id,
    psi.stage::text AS stage_type,
    COALESCE(j.name, 'Australia') AS jurisdiction,
    EXTRACT(YEAR FROM COALESCE(p.construction_start_date, p.commencement_of_operations, p.construction_end_date))::int AS construction_start_year,
    EXTRACT(YEAR FROM COALESCE(p.construction_end_date, p.construction_start_date, p.commencement_of_operations))::int AS construction_end_year,
    EXTRACT(YEAR FROM COALESCE(p.commencement_of_operations, p.construction_end_date, p.construction_start_date))::int AS operations_start_year,
    LEAST(GREATEST(COALESCE(p.operational_life_years, 50), 1), 50)::int AS reference_period_years
FROM project p
JOIN project_stage_instances psi ON psi.project_id = p.id
LEFT JOIN organization o ON o.id = p.proponent_org_id
LEFT JOIN jurisdictions j ON j.id = o.jurisdiction_id
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
  AND (
      CAST(:stage AS TEXT) IS NOT NULL
      OR psi.id = (
          SELECT psi2.id
          FROM project_stage_instances psi2
          WHERE psi2.project_id = p.id
          ORDER BY
              CASE psi2.stage::text
                  WHEN 'RECURRING' THEN 4
                  WHEN 'CONSTRUCTION' THEN 3
                  WHEN 'DESIGN' THEN 2
                  WHEN 'BUSINESS_CASE' THEN 1
                  ELSE 0
              END DESC,
              COALESCE(psi2.sequence, 0) DESC,
              psi2.created_on DESC,
              psi2.id DESC
          LIMIT 1
      )
  )
ORDER BY construction_start_year, operations_start_year, p.project_name
""")


def _empty_year_row(year: int) -> Dict[str, Decimal | int]:
    return {
        "year": year,
        "upfrontA1A5": Decimal(0),
        "useB1": Decimal(0),
        "maintenanceRepairReplacementRefurbishmentB2B5": Decimal(0),
        "operationalEnergyWaterB6B7": Decimal(0),
        "usersB8": Decimal(0),
        "totalEmissionsA1B8": Decimal(0),
        "centralCarbonValuePerTco2e": Decimal(0),
        "centralCarbonValue": Decimal(0),
        "lowCarbonValuePerTco2e": Decimal(0),
        "lowCarbonValue": Decimal(0),
        "highCarbonValuePerTco2e": Decimal(0),
        "highCarbonValue": Decimal(0),
    }


async def _fetch_electricity_by_year(
    db: AsyncSession,
    project_id: str,
    stage_instance_id: str,
    ui_table_key: str,
    elec_method: str,
) -> Dict[int, Decimal]:
    rs = await db.execute(
        _ELEC_BY_YEAR_SQL,
        {
            "project_id": project_id,
            "stage_instance_id": stage_instance_id,
            "ui_table_key": ui_table_key,
            "project_option_id": None,
            "submission_period_id": None,
        },
    )
    column = "market_based_tco2e" if elec_method == "market" else "location_based_tco2e"
    return {
        int(row["assessment_year"]): _dec(row[column])
        for row in rs.mappings().fetchall()
        if row["assessment_year"] is not None
    }


async def _fetch_b8_by_year(
    db: AsyncSession,
    project_id: str,
    stage_instance_id: str,
) -> Dict[int, Decimal]:
    rs = await db.execute(
        _B8_BY_YEAR_SQL,
        {
            "project_id": project_id,
            "stage_instance_id": stage_instance_id,
            "project_option_id": None,
            "submission_period_id": None,
        },
    )
    return {
        int(row["assessment_year"]): _dec(row["emissions_tco2e"])
        for row in rs.mappings().fetchall()
        if row["assessment_year"] is not None
    }


async def _fetch_price_lookup(
    db: AsyncSession,
    jurisdiction: str,
    year_start: int,
    year_end: int,
) -> Dict[str, Dict[int, Decimal]]:
    rs = await db.execute(
        _CARBON_PRICE_BY_YEAR_SQL,
        {
            "jurisdiction": jurisdiction,
            "year_start": year_start,
            "year_end": year_end,
        },
    )
    lookup: Dict[str, Dict[int, Decimal]] = {"central": {}, "low": {}, "high": {}}
    for row in rs.mappings().fetchall():
        range_code = (row["range_code"] or "").lower()
        if range_code in lookup:
            lookup[range_code][int(row["year"])] = _dec(row["value"])
    return lookup


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get(
    "/detail",
    response_model=OrgCarbonValuationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Org Carbon Valuation detail — yearly carbon valuation summary",
    description=(
        "Returns one yearly carbon valuation row across all matching projects in the organisation.\n\n"
        "Rows are aggregated by year so the org results grid matches the project carbon valuation table."
    ),
)
async def org_carbon_valuation_detail(
    org_id: UUID = Query(..., description="Organisation UUID"),
    project_class: Optional[str] = Query(None, description="Filter by project class (e.g. SMALL, LARGE)"),
    program_name: Optional[str] = Query(None, description="Filter by program name (case-insensitive)"),
    stage: Optional[str] = Query(None, description="Filter by stage type (e.g. CONSTRUCTION, RECURRING)"),
    elec_method: str = Query("location", description="Electricity accounting method: 'location' or 'market'"),
    project_type_id: Optional[UUID] = Query(None, description="Filter by project type (benchmark mastertype UUID)"),
    project_typecast: Optional[UUID] = Query(None, description="Filter by project typecast UUID"),
    db: AsyncSession = Depends(get_session),
) -> OrgCarbonValuationDetailResponse:
    elec_method = _normalize_elec_method(elec_method)

    params = _bind(
        org_id,
        project_class=_normalize_project_class(project_class),
        program_name=program_name,
        stage=_normalize_stage(stage),
        elec_method=elec_method,
        project_type_id=project_type_id,
        project_typecast_id=project_typecast,
    )
    try:
        result = await db.execute(_ELIGIBLE_PROJECTS_SQL, params)
        projects = result.mappings().all()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {exc}",
        ) from exc

    year_rows: Dict[int, Dict[str, Decimal | int]] = {}

    for project in projects:
        project_id = str(project["project_id"])
        stage_instance_id = str(project["stage_instance_id"])
        construction_start_year = project["construction_start_year"]
        construction_end_year = project["construction_end_year"]
        operations_start_year = project["operations_start_year"]

        if construction_start_year is None or construction_end_year is None or operations_start_year is None:
            continue

        reference_period_years = max(1, min(int(project["reference_period_years"]), _MAX_REFERENCE_PERIOD))
        reference_period_end_year = operations_start_year + reference_period_years
        construction_years = max(1, construction_end_year - construction_start_year + 1)

        module_result = await db.execute(
            _MODULE_SQL,
            {
                "project_id": project_id,
                "stage_instance_id": stage_instance_id,
                "elec_method": elec_method,
                "jurisdiction": project["jurisdiction"],
                "project_option_id": None,
                "submission_period_id": None,
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

        construction_elec_by_year = await _fetch_electricity_by_year(
            db, project_id, stage_instance_id, "electricity", elec_method
        )
        operations_elec_by_year = await _fetch_electricity_by_year(
            db, project_id, stage_instance_id, "opEnergyElectricity", elec_method
        )
        b8_year_map = await _fetch_b8_by_year(db, project_id, stage_instance_id)
        if not b8_year_map and b8_total != 0:
            annual_b8 = b8_total / Decimal(reference_period_years)
            for year in range(operations_start_year, reference_period_end_year + 1):
                b8_year_map[year] = annual_b8

        price_lookup = await _fetch_price_lookup(
            db,
            project["jurisdiction"],
            construction_start_year,
            reference_period_end_year,
        )

        construction_electricity_total = sum(construction_elec_by_year.values(), Decimal(0))
        operations_electricity_total = sum(operations_elec_by_year.values(), Decimal(0))
        upfront_total_a1_a5 = a1_a3 + a4 + a5
        upfront_excl_electricity = upfront_total_a1_a5 - construction_electricity_total
        b6_b7_total = b6_total + b7_total
        b6_b7_excl_electricity = b6_b7_total - operations_electricity_total

        annual_upfront_excl_elec = upfront_excl_electricity / Decimal(construction_years)
        annual_b1 = b1_total / Decimal(reference_period_years)
        annual_b2_b5 = b2_b5_total / Decimal(reference_period_years)
        annual_b6_b7_non_elec = b6_b7_excl_electricity / Decimal(reference_period_years)

        for year in range(construction_start_year, reference_period_end_year + 1):
            bucket = year_rows.setdefault(year, _empty_year_row(year))
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

            bucket["upfrontA1A5"] += upfront
            bucket["useB1"] += use_b1
            bucket["maintenanceRepairReplacementRefurbishmentB2B5"] += b2_b5
            bucket["operationalEnergyWaterB6B7"] += b6_b7
            bucket["usersB8"] += users_b8
            bucket["totalEmissionsA1B8"] += total
            bucket["centralCarbonValue"] += total * central_per
            bucket["lowCarbonValue"] += total * low_per
            bucket["highCarbonValue"] += total * high_per

    detail_rows: List[OrgCarbonValuationDetailRow] = []
    for year in sorted(year_rows):
        row_data = year_rows[year]
        total = row_data["totalEmissionsA1B8"]
        if total:
            row_data["centralCarbonValuePerTco2e"] = row_data["centralCarbonValue"] / total
            row_data["lowCarbonValuePerTco2e"] = row_data["lowCarbonValue"] / total
            row_data["highCarbonValuePerTco2e"] = row_data["highCarbonValue"] / total
        detail_rows.append(OrgCarbonValuationDetailRow(**row_data))

    total_gross = sum((r.totalEmissionsA1B8 for r in detail_rows), Decimal(0))
    total_central = sum((r.centralCarbonValue for r in detail_rows), Decimal(0))
    total_low = sum((r.lowCarbonValue for r in detail_rows), Decimal(0))
    total_high = sum((r.highCarbonValue for r in detail_rows), Decimal(0))

    return OrgCarbonValuationDetailResponse(
        rows=detail_rows,
        totals=OrgCarbonValuationTotals(
            total_gross_emissions_tco2e=total_gross,
            total_central_carbon_value=total_central,
            total_low_carbon_value=total_low,
            total_high_carbon_value=total_high,
        ),
    )

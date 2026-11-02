"""
routers/grade34_detailed_level_maintenance_calcs.py

API endpoint for Detailed Level - Maintenance, Repair, Replacement and Refurbishment
(B2-B5) Stage emissions calculations. Cell B227 area in Excel sheet 'MVP - Grade 1234'.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from services.grade34_detailed_level_maintenance_calcs import (
    Grade34MaintenanceRequest,
    Grade34MaintenanceResponse,
    calculator,
)

router = APIRouter(
    prefix="/api/grade34-maintenance-calculations",
    tags=["Maintenance Emissions Calculations - Grade 3/4 Detailed Level"],
)


@router.post(
    "/calculate",
    response_model=Grade34MaintenanceResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate Detailed Level - Maintenance (B2-5) Stage emissions",
    # description=(
    #     "Calculates emissions for a single row of the Detailed Level - Maintenance (B2-5) "
    #     "table, replicating the Excel formulas from tbl_detailed_level_calcs_maintenance88 "
    #     "and tbl_B1_calc_inuse_transport89 in 'MVP - Grade 1234'.\n\n"
    #     "**Required inputs:**\n"
    #     "- `jurisdiction` — e.g. 'Australia'\n"
    #     "- `operations_start_date` — start year, e.g. 2029 (cell C243)\n"
    #     "- `operations_end_date` — end year, e.g. 2100 (cell C244)\n"
    #     "- `emissions_category` — e.g. 'Fuels', 'Materials', 'Waste', 'Electricity'\n"
    #     "- `emissions_sub_category` — e.g. 'Liquid Fuels (Static)'\n"
    #     "- `emissions_source` — e.g. 'Diesel oil'\n"
    #     "- `period` — `'Annual'` or `'Total Operational Life'`\n"
    #     "- `unit` — unit of measure matching the source row, e.g. 'kL', 't'\n"
    #     "- `quantity` — quantity per event / per year in the stated unit\n\n"
    #     "**Computed internally:**\n"
    #     "- `reference_period` = MIN(ops_end − ops_start, 50) — cell C245\n"
    #     "- `effective_quantity` = reference_period × quantity (Annual) or quantity (Total Op Life)\n\n"
    #     "**Outputs:**\n"
    #     "- `scope1_emissions_tco2e` — Scope 1 EF × effective_quantity\n"
    #     "- `scope3_emissions_tco2e` — (Scope 3 EF × effective_quantity) + transport (Materials/Waste)\n"
    #     "- `total_emissions_tco2e` — Scope 1 + Scope 3\n"
    #     "- `b1_transport_detail` — intermediate tbl_B1_calc_inuse_transport89 data\n\n"
    #     "**Views used:**\n"
    #     "- `v_grade34_detailed_level` — emission factors\n"
    #     "- `v_transport_distances_lookup` — transport modes & distances (Materials/Waste only)\n"
    #     "- `v_densities_detailed_level` — density for unit-to-tonne conversion (Materials/Waste only)\n"
    # ),
)
async def calculate_grade34_maintenance_emissions(
    payload: Grade34MaintenanceRequest,
    db: AsyncSession = Depends(get_session),
) -> Grade34MaintenanceResponse:
    """
    Calculate Detailed Level - Maintenance (B2-5) Stage emissions for one row.
    Returns 422 for validation errors, 500 for unexpected calculation errors.
    """
    try:
        return await calculator.calculate(db, payload)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Calculation failed: {type(e).__name__}: {e}",
        )

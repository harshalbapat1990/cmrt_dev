"""
routers/detailed_level_fuel_water.py

API endpoint for Operational Energy (B6) and Water (B7) - Detailed Level -
Operations (B6-7) Stage (Fuel and Water ONLY) emissions calculations.

Excel source: tbl_detailed_level_calcs_operational_fuel_water
Sheet: MVP - Grade 1234
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from services.detailed_level_calcs_operational_fuel_water import (
    DetailedLevelFuelWaterRequest,
    DetailedLevelFuelWaterResponse,
    calculator,
)

router = APIRouter(
    prefix="/api/detailed-level-fuel-water-calculations",
    tags=["Operational Emissions Calculations - Grade 3/4 Detailed Level Fuel & Water (B6-7)"],
)


@router.post(
    "/calculate",
    response_model=DetailedLevelFuelWaterResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate Detailed Level - Operational Fuel & Water (B6-7) Stage emissions",
    # description=(
    #     "Calculates emissions for a single row of the Operational Energy (B6) and "
    #     "Water (B7) Detailed Level table, replicating the Excel formulas from "
    #     "tbl_detailed_level_calcs_operational_fuel_water in 'MVP - Grade 1234'.\n\n"
    #     "**Required inputs:**\n"
    #     "- `jurisdiction` — e.g. 'Australia'\n"
    #     "- `emissions_category` — e.g. 'Fuels', 'Water'\n"
    #     "- `emissions_sub_category` — e.g. 'Liquid Fuels (Static)'\n"
    #     "- `emissions_source` — e.g. 'Diesel oil'\n"
    #     "- `quantity` — quantity in the stated unit\n\n"
    #     "**Optional inputs:**\n"
    #     "- `unit` — unit of measure (e.g. 'kL'); used to narrow the factor lookup\n"
    #     "- `notes` — free-text; echoed in response\n\n"
    #     "**Outputs:**\n"
    #     "- `scope1_emissions_tco2e` — scope 1 factor × quantity (0 when factor not found)\n"
    #     "- `scope2_emissions_tco2e` — always 0 (placeholder)\n"
    #     "- `scope3_emissions_tco2e` — scope 3 factor × quantity (0 when factor not found)\n"
    #     "- `emissions_tco2e` — total; non-zero only when category is 'Fuels' or 'Electricity'\n\n"
    #     "**View used:** `v_grade34_detailed_level`\n"
    # ),
)
async def calculate_fuel_water_emissions(
    payload: DetailedLevelFuelWaterRequest,
    db: AsyncSession = Depends(get_session),
) -> DetailedLevelFuelWaterResponse:
    """
    Calculate Detailed Level - Operational Fuel & Water (B6-7) Stage emissions for one row.
    Returns 500 for unexpected calculation errors.
    """
    try:
        return await calculator.calculate(db, payload)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Calculation failed: {type(e).__name__}: {e}",
        )

"""
routers/maintenance_replacement_component_level_calcs.py

API endpoint for Component Level - Maintenance (B2-5) Stage emissions calculations.
Cell B227 in Excel sheet 'MVP - Grade 1234'.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from services.maintenance_replacement_component_level_calcs import (
    MaintenanceCalcRequest,
    MaintenanceCalcResponse,
    calculator,
)

router = APIRouter(
    prefix="/api/maintenance-calculations",
    tags=["Maintenance Emissions Calculations - Component Level"],
)


@router.post(
    "/calculate",
    response_model=MaintenanceCalcResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate Component Level - Maintenance (B2-5) Stage emissions",
    # description=(
    #     "Calculates emissions for a single row of the Maintenance & Replacement component level table, "
    #     "replicating the Excel formulas from 'MVP - Grade 1234' sheet (cell B227).\n\n"
    #     "**Required inputs:**\n"
    #     "- `jurisdiction` — e.g. 'Australia', 'New Zealand'\n"
    #     "- `activity_type` — e.g. 'Road resurface', 'Road reconstruction'\n"
    #     "- `item` — e.g. 'Local road - rural'\n"
    #     "- `unit` — unit of measure, e.g. 'm2'\n"
    #     "- `quantity` — quantity per maintenance event\n"
    #     "- `reference_period` — reference period in years (cell $C$225 in Excel)\n"
    #     "- `frequency_years` — maintenance interval in years ([@[Frequency (years)]] in Excel)\n\n"
    #     "**Outputs:**\n"
    #     "- `number_of_occurrences` — FLOOR(design_life / frequency, 1)\n"
    #     "- `scope3_emissions_tco2e` — occurrences × quantity × emissions_intensity\n"
    #     "- `total_emissions_tco2e` — occurrences + scope3 (as per Excel formula)\n\n"
    #     "**View used:**\n"
    #     "- `v_maintenance_replacement_component_level`\n"
    # ),
)
async def calculate_maintenance_emissions(
    payload: MaintenanceCalcRequest,
    db: AsyncSession = Depends(get_session),
) -> MaintenanceCalcResponse:
    """
    Calculate Component Level - Maintenance (B2-5) Stage emissions for one row.
    Returns 500 for unexpected calculation errors.
    """
    try:
        return await calculator.calculate(db, payload)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Calculation failed: {type(e).__name__}: {e}",
        )

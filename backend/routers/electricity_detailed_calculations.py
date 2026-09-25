"""
routers/electricity_detailed_calculations.py

API endpoint for Detailed Level - Electricity emissions calculations.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from services.electricity_detailed_calculations import (
    ElectricityDetailedRequest,
    ElectricityDetailedResponse,
    calculator,
)

router = APIRouter(
    prefix="/api/electricity-detailed-calculations",
    tags=["Construction Emissions Calculations - Detailed Level Electricity"],
)


@router.post(
    "/calculate",
    response_model=ElectricityDetailedResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate Detailed Level - Electricity emissions",
)
async def calculate_electricity_detailed_emissions(
    payload: ElectricityDetailedRequest,
    db: AsyncSession = Depends(get_session),
) -> ElectricityDetailedResponse:
    """
    Calculate Detailed Level - Electricity emissions for one row.

    Looks up all five factor types (scope2_location, scope3_location,
    scope2_market, scope3_market, renewable_pct) from electric_decarb_factors
    for the supplied jurisdiction / region / year, then applies the
    IFS-multiplier × quantity × factor formulas from the Excel model.
    """
    try:
        return await calculator.calculate(db, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Calculation failed: {type(e).__name__}: {e}",
        )

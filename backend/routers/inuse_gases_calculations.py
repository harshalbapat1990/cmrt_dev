"""
routers/inuse_gases_calculations.py

API endpoints for In-Use (B1) Gases component-level emissions calculations.
Exposes InUseGasesCalculator service via REST API.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from services.inuse_gases_component_level_calcs import (
    InUseGasesRequest,
    InUseGasesResponse,
    calculator,
)

router = APIRouter(
    prefix="/api/inuse-gases-calculations",
    tags=["Operations and Maintenance - Use (B1) In-Use Gases Component Level"],
)


@router.post(
    "/calculate",
    response_model=InUseGasesResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate In-Use (B1) gases component-level emissions",
)
async def calculate_inuse_gases_emissions(
    payload: InUseGasesRequest,
    db: AsyncSession = Depends(get_session),
) -> InUseGasesResponse:
    """
    Calculate In-Use (B1) gases component-level Scope 1 (fugitive) emissions.

    Steps:
    1. Looks up annual leakage rate from fugitive_equipment table
       by Jurisdiction + Application Type.

    2. Looks up Scope 1 emissions factor from v_grade34_detailed_level
       by Jurisdiction + Gas (Emissions Source).

    3. Calculates Scope 1 emissions:
       Scope1 = Annual_Leakage_Rate(%) × Charge(kg) / 1000
                × Scope1_Factor(tCO2e/kg) × Reference_Period(years)

    4. Reference Period = MIN(ops_end - ops_start, 50), capped at 50 years.
    """
    try:
        result = await calculator.calculate(db, payload)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Calculation failed: {str(e)}",
        )

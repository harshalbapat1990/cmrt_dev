"""
routers/grade2_calculations.py

API endpoints for Grade 2 component-level emissions calculations.
Exposes Grade2ComponentCalculator service via REST API.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from services.grade2_component_calculations import (
    Grade2CalculationRequest,
    Grade2CalculationResponse,
    calculator,
)

router = APIRouter(
    prefix="/api/grade2-calculations",
    tags=["Construction Emissions Calculations - Grade 2 Component Level"],
)


@router.post(
    "/calculate",
    response_model=Grade2CalculationResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate Grade 2 component-level emissions",
)
async def calculate_grade2_emissions(
    payload: Grade2CalculationRequest,
    db: AsyncSession = Depends(get_session),
) -> Grade2CalculationResponse:
    """
    Calculate Grade 2 component-level emissions.

    Looks up emission factors from the v_grade2_component_level PostgreSQL view
    matching on Jurisdiction + Emissions Category + Emissions Sub-Category +
    Emissions Source, then multiplies each factor by the supplied Quantity.
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

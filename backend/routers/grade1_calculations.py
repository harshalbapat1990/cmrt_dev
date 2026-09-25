"""
routers/grade1_calculations.py

API endpoints for Grade 1 asset-level emissions calculations.
Exposes Grade1AssetCalculator service via REST API.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Union

from core.session import get_session
from services.grade1_asset_calculations import (
    Grade1CalculationRequest,
    Grade1CalculationResponse,
    Grade1BatchCalculationRequest,
    Grade1BatchCalculationResponse,
    calculator,
)

router = APIRouter(
    prefix="/api/grade1-calculations",
    tags=["Construction Emissions Calculations - Grade 1 Asset Level"],
)


@router.post(
    "/calculate",
    response_model=Union[Grade1CalculationResponse, Grade1BatchCalculationResponse],
    status_code=status.HTTP_200_OK,
    summary="Calculate Grade 1 asset-level emissions",
    description=(
        "Accepts a **single** request object or a **list** of request objects.\n\n"
        "Single request returns a `Grade1CalculationResponse`.\n"
        "Array request returns a `Grade1BatchCalculationResponse` with per-item "
        "results and any per-item errors (failures do not abort the batch).\n\n"
        "Fields per item:\n"
        "- Jurisdiction, Mastertype, Typecast (lookups)\n"
        "- Sensitivity level (Low/Mid/High)\n"
        "- Quantity (CAPEX in $ or other functional units)\n\n"
        "Returns emissions breakdown by lifecycle stage (A1-A3, A4, A5)."
    ),
)
async def calculate_emissions(
    payload: Union[List[Grade1CalculationRequest], Grade1CalculationRequest],
    db: AsyncSession = Depends(get_session),
) -> Union[Grade1CalculationResponse, Grade1BatchCalculationResponse]:
    """
    Calculate Grade 1 asset-level emissions — single or batch.

    The calculation uses the v_grade1_asset_level_pivoted PostgreSQL view
    as the lookup table. Formula:

    Product Stage (A1-A3):
      Emissions = Material Share (%) × Quantity × Emission Intensity (tCO2e/$ material)

    Transport (A4) & Construction (A5):
      Emissions = Quantity × Emission Intensity (tCO2e/$ material)
    """

    try:
        if isinstance(payload, list):
            return await calculator.calculate_batch(db, payload)
        return await calculator.calculate(db, payload)
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

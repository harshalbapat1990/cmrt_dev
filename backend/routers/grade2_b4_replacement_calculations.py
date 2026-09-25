from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from core.session import get_session
from services.grade2_b4_replacement_calculations import (
    Grade2B4ReplacementRequest,
    Grade2B4ReplacementResponse,
    calculator,
)

router = APIRouter(
    prefix="/api/grade2-b4-replacement",
    tags=["Grade 2 Component Level Replacement (B4)"],
)


@router.post(
    "/calculate",
    response_model=Grade2B4ReplacementResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate Component Level Replacement (B4) emissions",
)
async def calculate_b4_replacement_emissions(
    payload: Grade2B4ReplacementRequest,
    db: AsyncSession = Depends(get_session),
) -> Grade2B4ReplacementResponse:
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
            detail=f"B4 replacement calculation failed: {str(e)}",
        )

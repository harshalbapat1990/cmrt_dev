"""
routers/grade2_calculations.py

API endpoints for Grade 2 component-level emissions calculations.
Exposes Grade2ComponentCalculator service via REST API.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from core.security import Principal, get_current_principal
from core.dataset_authorization import (
    assert_dataset_revision_read_permission,
    assert_project_dataset_revision_read_permission,
)
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
    principal: Principal = Depends(get_current_principal),
) -> Grade2CalculationResponse:
    """
    Calculate Grade 2 component-level emissions.

    Looks up Grade 2 emission factors from the authorized revision and multiplies
    each factor by the supplied quantity.
    """
    try:
        if payload.project_id is not None:
            revision_id = await assert_project_dataset_revision_read_permission(
                db, principal, payload.project_id, payload.dataset_revision_id
            )
        elif payload.dataset_revision_id is not None:
            revision_id = payload.dataset_revision_id
            await assert_dataset_revision_read_permission(db, principal, revision_id)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="project_id or dataset_revision_id is required for Grade 2 calculations",
            )
        authorized_payload = payload.model_copy(update={"dataset_revision_id": revision_id})
        result = await calculator.calculate(db, authorized_payload)
        return result
    except HTTPException:
        raise
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

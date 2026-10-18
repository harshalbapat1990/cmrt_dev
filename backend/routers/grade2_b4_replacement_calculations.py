from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from core.session import get_session
from core.security import Principal, get_current_principal
from core.dataset_authorization import assert_project_dataset_revision_read_permission
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
    principal: Principal = Depends(get_current_principal),
) -> Grade2B4ReplacementResponse:
    try:
        revision_id = await assert_project_dataset_revision_read_permission(
            db, principal, payload.project_id, payload.dataset_revision_id
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
            detail=f"B4 replacement calculation failed: {str(e)}",
        )

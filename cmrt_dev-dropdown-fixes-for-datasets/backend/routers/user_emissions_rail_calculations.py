"""
routers/user_emissions_rail_calculations.py

API endpoints for Rail user-emissions (B8) calculations.

Applies to both AUS and NZ projects; Small and Large projects use the same
calculation logic.  Jurisdiction (AUS vs NZ) is resolved server-side.

Endpoints:
  POST   /api/user-emissions/rail/calculate
      — Pure calculation (no storage).  Accepts terrain + freight quantity
        per train type; returns per-train-type results and interim total.
        Frontend stores inputs in activity_data (ui_table_key='railUsers').
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from core.security import get_current_principal, Principal
from schemas.user_emissions_rail import (
    RailEmissionsCalculateRequest,
    RailEmissionsCalculateResponse,
)
from services.user_emissions_rail_calculations import calculate_rail

router = APIRouter(
    prefix="/api/user-emissions/rail",
    tags=["User Emissions - Rail (B8)"],
)


# ─────────────────────────────────────────────────────────────────────────────
# POST /calculate  — pure calculation, no storage
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/calculate",
    response_model=RailEmissionsCalculateResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate rail user emissions",
    description=(
        "Single-row rail user-emissions calculation. "
        "Pass one rail_type + terrain + freight_quantity per call.\n\n"
        "Returns all calculated fields (fuel consumption, fuel volume, "
        "emissions intensity, annual emissions, total reference period emissions) "
        "together with the echoed inputs and project parameters.\n\n"
        "No data is written to the database — inputs are owned by the frontend "
        "(activity_data table, ui_table_key='railUsers').\n\n"
        "Jurisdiction (AUS vs NZ) is resolved from the project's proponent "
        "organisation region and determines whether 'Diesel oil' or 'Diesel' "
        "emission factors are used."
    ),
)
async def calculate_rail_emissions(
    payload: RailEmissionsCalculateRequest,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
) -> RailEmissionsCalculateResponse:
    try:
        return await calculate_rail(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rail emissions calculation failed: {exc}",
        )

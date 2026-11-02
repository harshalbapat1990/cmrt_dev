"""
routers/operational_component_level_calcs.py

POST /api/operational-calculations/calculate
  → Computes Component Level Operational Energy (B6) emissions for one row.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from services.operational_component_level_calcs import (
    OperationalComponentRequest,
    OperationalComponentResponse,
    calculator,
)

router = APIRouter(
    prefix="/api/operational-calculations",
    tags=["Operational Energy - Component Level (B6)"],
)


@router.post(
    "/calculate",
    response_model=OperationalComponentResponse,
    summary="Calculate Component Level Operational Energy emissions (B6)",
    # description=(
    #     "Computes Location-Based and Market-Based electricity emissions for one row of "
    #     "tbl_component_level_operational, summed across the reference period "
    #     "(MIN(ops_end - ops_start, 50) years starting from ops_start).\n\n"
    #     "The emissions source is looked up in the operational_equipment table to obtain "
    #     "annual electricity consumption (MWh/year per unit). If not found the quantity is "
    #     "treated directly as MWh/year (e.g. for Onsite/Offsite Renewable Electricity).\n\n"
    #     "Electricity decarbonisation factors are fetched from electric_decarb_factors and summed "
    #     "year-by-year across the operational period."
    # ),
)
async def calculate_operational_component(
    payload: OperationalComponentRequest,
    db: AsyncSession = Depends(get_session),
) -> OperationalComponentResponse:
    try:
        return await calculator.calculate(db=db, request=payload)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

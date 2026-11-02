"""
Router for B1 Detailed Level Maintenance emissions calculations.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from services.detailed_level_maintenance_calcs import (
    DetailedMaintenanceRequest,
    DetailedMaintenanceRowResponse,
    calculator,
)

router = APIRouter(prefix="/api/detailed-level-maintenance-calculations", tags=["Maintenance"])


@router.post(
    "/calculate",
    response_model=DetailedMaintenanceRowResponse,
    summary="Calculate B1 Maintenance Emissions (Detailed Level)",
    # description="""
    # Calculate Scope 1 and Scope 3 emissions for a maintenance activity.
    
    # Formulas:
    # - Quantity Used: Reference_Period × Quantity (if Annual), else Quantity (if Total Operational Life)
    # - Scope 1 = Scope1_Factor × Quantity Used
    # - Scope 3 = Scope3_Factor × Quantity Used
    # - Total = Scope 1 + Scope 3
    # """,
)
async def calculate_maintenance_emissions(
    request: DetailedMaintenanceRequest,
    db: AsyncSession = Depends(get_session),
) -> DetailedMaintenanceRowResponse:
    """
    Calculate operational maintenance emissions for a single B1 maintenance row.
    
    Looks up Scope 1 and Scope 3 factors from v_grade34_detailed_level view
    and applies the appropriate formula based on period type.
    """
    return await calculator.calculate(db, request)

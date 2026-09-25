"""
Router for B2-B5 Detailed Level Maintenance emissions calculations.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from services.detailed_level_maintenance_b2_b5_calcs import (
    DetailedMaintenanceB2B5Request,
    DetailedMaintenanceB2B5Response,
    calculator,
)

router = APIRouter(
    prefix="/api/detailed-level-maintenance-b2-b5-calculations",
    tags=["Maintenance (B2-B5)"],
)


@router.post(
    "/calculate",
    response_model=DetailedMaintenanceB2B5Response,
    summary="Calculate B2-B5 Maintenance Emissions (Detailed Level)",
    # description="""
    # Calculate Scope 1 and Scope 3 emissions for maintenance, repair, 
    # replacement, and refurbishment (B2-B5) activities.
    
    # Formulas:
    # - Quantity Used: Reference_Period × Quantity (if Annual), else Quantity (if Total Operational Life)
    # - Scope 1 = Scope1_Factor × Quantity Used
    # - Scope 3 = (Scope3_Factor × Quantity Used) + Transport (for Materials/Waste only)
    # - Transport = SUMPRODUCT(distances × EFs) × Tonnage Conversion
    # - Total = Scope 1 + Scope 3
    # """,
)
async def calculate_maintenance_b2_b5_emissions(
    request: DetailedMaintenanceB2B5Request,
    db: AsyncSession = Depends(get_session),
) -> DetailedMaintenanceB2B5Response:
    """
    Calculate operational B2-B5 maintenance emissions for a single row.
    
    Includes transport component for Materials and Waste categories,
    using intermediate tbl_B1_calc_inuse_transport89 logic.
    """
    return await calculator.calculate(db, request)

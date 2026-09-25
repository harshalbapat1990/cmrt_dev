"""
routers/grade34_construction_calculations.py

API endpoint for Grade 3/4 Detailed Level - Construction Stage (A5) emissions calculations.
Exposes Grade34ConstructionCalculator service via REST API.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from services.grade34_detailed_level_construction_calcs import (
    Grade34ConstructionRequest,
    Grade34ConstructionResponse,
    calculator,
)

router = APIRouter(
    prefix="/api/grade34-construction-calculations",
    tags=["Construction Emissions Calculations - Grade 3/4 Detailed Level"],
)


@router.post(
    "/calculate",
    response_model=Grade34ConstructionResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate Grade 3/4 Detailed Level - Construction Stage emissions",
    # description=(
    #     "Calculates emissions for a single row of the Detailed Level - Construction Stage "
    #     "(Grade 3/4) table, replicating the Excel formulas from tbl_detailed_level_calcs_construction.\n\n"
    #     "**Required inputs:**\n"
    #     "- `jurisdiction` — e.g. 'Australia'\n"
    #     "- `emissions_category` — e.g. 'Fuels', 'Materials', 'Gases', 'Water', 'Waste', 'Vegetation', 'Electricity'\n"
    #     "- `emissions_sub_category` — e.g. 'Liquid Fuels (Static)', 'Asphalt'\n"
    #     "- `emissions_source` — e.g. 'Diesel oil', 'Hot mix asphalt, 4%'\n"
    #     "- `unit` — unit of measure matching the source row (e.g. 'kL', 't', 'm3')\n"
    #     "- `quantity` — user-entered quantity in the above unit\n\n"
    #     "**Outputs:**\n"
    #     "- Scope 1 & Scope 3 base emissions\n"
    #     "- Product Stage A1-3, Transport Stage A4, Construction Stage A5 (tCO2e)\n"
    #     "- Total emissions (tCO2e)\n"
    #     "- Intermediate A4 transport detail (tonnage, modes, distances, EFs)\n\n"
    #     "**Views used:**\n"
    #     "- `v_grade34_detailed_level` — emission factors\n"
    #     "- `v_transport_distances_lookup` — transport modes & distances (Materials/Waste only)\n"
    #     "- `v_densities_detailed_level` — density for unit-to-tonne conversion (Materials/Waste only)\n"
    # ),
)
async def calculate_grade34_construction_emissions(
    payload: Grade34ConstructionRequest,
    db: AsyncSession = Depends(get_session),
) -> Grade34ConstructionResponse:
    """
    Calculate Grade 3/4 Detailed Level - Construction Stage emissions for one row.

    Raises 400 if no matching emission factor data is found.
    Raises 500 for unexpected calculation errors.
    """
    try:
        return await calculator.calculate(db, payload)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Calculation failed: {type(e).__name__}: {e}",
        )

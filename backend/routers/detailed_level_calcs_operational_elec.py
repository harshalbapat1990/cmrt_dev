"""
routers/detailed_level_calcs_operational_elec.py

API endpoint for Operational Energy (B6) and Water (B7) - Detailed Level -
Operations (B6-7) Stage (Electricity ONLY) calculations.

Excel source: tbl_detailed_level_calcs_operational_elec
Sheet: MVP - Grade 1234
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from services.detailed_level_calcs_operational_elec import (
    OperationalElecRequest,
    OperationalElecResponse,
    calculator,
)

router = APIRouter(
    prefix="/api/detailed-level-operational-elec-calculations",
    tags=["Operational Emissions Calculations - Grade 3/4 Detailed Level Electricity (B6-7)"],
)


@router.post(
    "/calculate",
    response_model=OperationalElecResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate Detailed Level - Operational Electricity (B6-7) Stage emissions",
    # description=(
    #     "Calculates emissions for a single row of the Operational Energy (B6) / "
    #     "Water (B7) Detailed Level Electricity table, replicating the Excel formulas "
    #     "from tbl_detailed_level_calcs_operational_elec in 'MVP - Grade 1234'.\n\n"
    #     "**Required inputs:**\n"
    #     "- `jurisdiction` — e.g. 'Australia' (cell C804 in Excel)\n"
    #     "- `region` — grid region / state for location-based EF (e.g. 'New South Wales') "
    #     "(cell C805 in Excel)\n"
    #     "- `emission_source` — one of: 'Grid Electricity', "
    #     "'Onsite Renewable Electricity', 'Offsite Renewable Electricity'\n"
    #     "- `year` — calendar year (2026–2100)\n"
    #     "- `quantity_mwh` — electricity quantity in MWh\n\n"
    #     "**Optional inputs:**\n"
    #     "- `unit` — unit label, echoed only\n"
    #     "- `notes` — free-text, echoed only\n"
    #     "- `dataset_revision_id` — pin to a specific factor revision (UUID)\n\n"
    #     "**Multipliers (Excel IFS):**\n"
    #     "- Grid Electricity: LB = +1, MB = +1\n"
    #     "- Onsite Renewable: LB = −1, MB = −1\n"
    #     "- Offsite Renewable: LB = 0, MB = −1\n\n"
    #     "**Outputs (tCO2e):**\n"
    #     "- `location_based_emissions_tco2e` = Scope2_LB + Scope3_LB\n"
    #     "- `market_based_emissions_tco2e` = Scope2_MB + Scope3_MB\n"
    #     "- `scope2_location_based_tco2e`, `scope2_market_based_tco2e`\n"
    #     "- `scope3_location_based_tco2e`, `scope3_market_based_tco2e`\n\n"
    #     "**View used:** `v_elec_decarb_scenarios`\n"
    # ),
)
async def calculate_operational_elec_emissions(
    payload: OperationalElecRequest,
    db: AsyncSession = Depends(get_session),
) -> OperationalElecResponse:
    """
    Calculate Detailed Level - Operational Electricity (B6-7) Stage emissions for one row.
    Returns 422 for validation errors, 500 for unexpected calculation errors.
    """
    try:
        return await calculator.calculate(db, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Calculation failed: {type(e).__name__}: {e}",
        )

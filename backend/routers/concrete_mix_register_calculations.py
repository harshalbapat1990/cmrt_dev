"""
routers/concrete_mix_register_calculations.py

API endpoints for the Concrete Register (MVP) calculation.

Endpoints:
  POST /api/concrete-register/calculate
      — Accepts a single ConcreteMixCalculateRequest OR a list of them.
        Calculates SCM-adjusted quantities, component EFs, transport EFs,
        GWP A1-A3, Transport A4, and total emissions on-the-fly.
        Nothing is stored — results are returned directly.

  POST /api/concrete-register/calculate-epd-shortcut
      — Accepts a ConcreteEPDShortcutRequest where the user supplies GWP A1-3
        directly from an EPD document (kgCO2e/m3).
        Transport A4 is calculated from the DB the same way as the detailed path.
        Nothing is stored — results are returned directly.
"""

from typing import List, Union

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from services.concrete_mix_register_calculations import (
    ConcreteMixCalculateRequest,
    ConcreteMixCalculateResponse,
    ConcreteEPDShortcutRequest,
    ConcreteEPDShortcutResponse,
    ConcreteSimplifiedRegisterRequest,
    ConcreteSimplifiedRegisterResponse,
    calculate_epd_shortcut,
    calculate_simplified_register,
    calculator,
)

router = APIRouter(
    prefix="/api/concrete-register",
    tags=["Concrete Register"],
)


@router.post(
    "/calculate",
    response_model=Union[ConcreteMixCalculateResponse, List[ConcreteMixCalculateResponse]],
    status_code=status.HTTP_200_OK,
    summary="Calculate concrete mix design emission factors",
    # description=(
    #     "Accepts a single concrete mix or a list of mixes.\n\n"
    #     "For each mix the service:\n"
    #     "1. Applies SCM substitution to binder quantities "
    #     "(General Purpose Cement / Fly Ash / GGBF Slag)\n"
    #     "2. Looks up Scope 3 EFs from v_grade34_detailed_level\n"
    #     "3. Looks up transport distances from v_transport_distances_lookup\n"
    #     "4. Calculates component + transport EFs for A1-A3 (tCO2e/m3)\n"
    #     "5. Adds Transport Stage A4 (delivery of finished concrete to site)\n"
    #     "6. Multiplies by volume for total emissions\n"
    #     "7. Returns the EF label for Grade 3-4 dataset registration (Part 3)\n\n"
    #     "No data is stored — results are calculated and returned on-the-fly."
    # ),
)
async def calculate_concrete_mix(
    payload: Union[ConcreteMixCalculateRequest, List[ConcreteMixCalculateRequest]],
    db: AsyncSession = Depends(get_session),
) -> Union[ConcreteMixCalculateResponse, List[ConcreteMixCalculateResponse]]:
    try:
        if isinstance(payload, list):
            return await calculator.calculate_batch(db, payload)
        return await calculator.calculate(db, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Calculation failed: {str(exc)}",
        )


@router.post(
    "/calculate-epd-shortcut",
    response_model=ConcreteEPDShortcutResponse,
    status_code=status.HTTP_200_OK,
    summary="EPD Shortcut — calculate total emissions from a known EPD GWP A1-3 value",
    # description=(
    #     "Use this endpoint when the GWP Total A1-3 (kgCO2e/m3) is already known "
    #     "from a product EPD document, bypassing the detailed component calculation.\n\n"
    #     "The service:\n"
    #     "1. Accepts the user-supplied GWP A1-3 value directly\n"
    #     "2. Calculates Transport Stage A4 from the DB (same logic as /calculate)\n"
    #     "3. Returns total emissions = (GWP A1-3 + A4) × volume_m3\n\n"
    #     "No data is stored — results are calculated and returned on-the-fly."
    # ),
)
async def calculate_concrete_mix_epd_shortcut(
    payload: ConcreteEPDShortcutRequest,
    db: AsyncSession = Depends(get_session),
) -> ConcreteEPDShortcutResponse:
    try:
        return await calculate_epd_shortcut(db, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"EPD Shortcut calculation failed: {str(exc)}",
        )


@router.post(
    "/calculate-simplified",
    response_model=ConcreteSimplifiedRegisterResponse,
    status_code=status.HTTP_200_OK,
    summary="Simplified Register — calculate emissions from BAU default mix with target SCM content",
    # description=(
    #     "Calculates concrete emissions using the BAU default mix compositions "
    #     "for the given strength grade, adjusted for the user-supplied Target SCM Content.\n\n"
    #     "**SCM adjustment rules (differ from the detailed mix path):**\n"
    #     "- `total_cementitious` = GPC + FA + GGBF from BAU table for the given strength\n"
    #     "- `default_max_fa_frac` = FA_bau / total_cementitious\n"
    #     "- GPC  = total_cementitious × (1 − scm_pct / 100)\n"
    #     "- FA   = total_cementitious × min(scm_pct / 100, default_max_fa_frac)\n"
    #     "- GGBF = total_cementitious × max(0, scm_pct / 100 − default_max_fa_frac)\n"
    #     "- All other materials (aggregates, water, admixture) use BAU table values unchanged\n\n"
    #     "**Identical to the detailed mix path for:**\n"
    #     "- Component EF lookups (v_grade34_detailed_level)\n"
    #     "- Transport distance lookups (v_transport_distances_lookup)\n"
    #     "- Production Stage A3 (concrete_mix_production)\n"
    #     "- Transport Stage A4 (concrete delivery to site)\n\n"
    #     "**BAU baseline** uses the same BAU quantities with 0% SCM "
    #     "(all cementitious as GPC, no FA or GGBF). "
    #     "Returns `bau_a1a3_tco2e_m3` and `base_case_emissions_tco2e` for comparison.\n\n"
    #     "No data is stored — results are calculated and returned on-the-fly."
    # ),
)
async def calculate_concrete_simplified_register(
    payload: ConcreteSimplifiedRegisterRequest,
    db: AsyncSession = Depends(get_session),
) -> ConcreteSimplifiedRegisterResponse:
    try:
        return await calculate_simplified_register(db, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simplified Register calculation failed: {str(exc)}",
        )

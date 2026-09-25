"""
routers/user_emissions_nz_calculations.py

API endpoints for the NZ small-project user-emissions (B8) calculation.

Endpoints:
  POST   /api/user-emissions/nz/calculate
      — Run VEPM-based calculation for all reference-period years, store
        per-year results, return interim + final user emissions.
        Inputs (VKT/speeds) are passed per call — NOT stored by this service.

  GET    /api/user-emissions/nz/results
      — List per-year result rows for a project/stage + option.

  GET    /api/user-emissions/nz/summary
      — Return interim absolute + final user emissions for every option in a
        stage instance (final = option − base-case).
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from core.security import get_current_principal, Principal
from models.project_options import ProjectOption
from models.user_emissions_nz import UserEmissionsNzResult
from schemas.user_emissions_nz import (
    NzEmissionsCalculateRequest,
    NzEmissionsCalculateResponse,
    NzEmissionsSummaryResponse,
    NzOptionSummary,
    UserEmissionsNzResultOut,
)
from services.user_emissions_nz_calculations import calculate_and_store_nz

router = APIRouter(
    prefix="/api/user-emissions/nz/roads",
    tags=["User Emissions - NZ (B8)"],
)


# ─────────────────────────────────────────────────────────────────────────────
# POST /calculate  — run calculation, store results
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/calculate",
    response_model=NzEmissionsCalculateResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate & store NZ user emissions",
    description=(
        "Accepts Road Users inputs (VKT + average speed per vehicle type) for one "
        "project option.  Runs the VEPM linear-interpolation calculation for every "
        "year in the project's reference period and stores per-year results.  "
        "Returns interim absolute emissions (tCO2e) = Σ annual emissions.\n\n"
        "Re-calling this endpoint with the same option overwrites previous results."
    ),
)
async def calculate_nz_emissions(
    payload: NzEmissionsCalculateRequest,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
) -> NzEmissionsCalculateResponse:
    try:
        result = await calculate_and_store_nz(db, payload)
        await db.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Calculation failed: {exc}",
        )


# ─────────────────────────────────────────────────────────────────────────────
# GET /results  — per-year results for one option
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/results",
    response_model=List[UserEmissionsNzResultOut],
    summary="List per-year NZ user-emissions results",
)
async def list_results(
    project_id: UUID = Query(...),
    project_stage_instance_id: UUID = Query(...),
    project_option_id: UUID = Query(...),
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
) -> List[UserEmissionsNzResultOut]:
    rows = (
        await db.execute(
            select(UserEmissionsNzResult).where(
                UserEmissionsNzResult.project_id == project_id,
                UserEmissionsNzResult.project_stage_instance_id == project_stage_instance_id,
                UserEmissionsNzResult.project_option_id == project_option_id,
            ).order_by(UserEmissionsNzResult.assessment_year)
        )
    ).scalars().all()
    return [UserEmissionsNzResultOut.model_validate(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# GET /summary  — interim + final emissions for all options in a stage instance
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/summary",
    response_model=NzEmissionsSummaryResponse,
    summary="Interim & final NZ user emissions by option",
    description=(
        "Returns interim absolute emissions per option and the final user emissions "
        "(option − base-case).  The base-case option is identified by is_default=true "
        "on project_options."
    ),
)
async def get_summary(
    project_id: UUID = Query(...),
    project_stage_instance_id: UUID = Query(...),
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
) -> NzEmissionsSummaryResponse:
    # Fetch all options for this stage instance
    options_rows = (
        await db.execute(
            select(ProjectOption).where(
                ProjectOption.project_id == project_id,
                ProjectOption.stage_instance_id == project_stage_instance_id,
            )
        )
    ).scalars().all()

    if not options_rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No project options found for this stage instance.",
        )

    # Sum per-year results per option
    sums_rows = (
        await db.execute(
            select(
                UserEmissionsNzResult.project_option_id,
                func.sum(UserEmissionsNzResult.total_annual_emissions_tco2e).label("interim"),
            ).where(
                UserEmissionsNzResult.project_id == project_id,
                UserEmissionsNzResult.project_stage_instance_id == project_stage_instance_id,
            ).group_by(UserEmissionsNzResult.project_option_id)
        )
    ).mappings().all()

    interim_by_option: dict[UUID, float] = {
        r["project_option_id"]: r["interim"] for r in sums_rows
    }

    # Identify base-case option
    base_case_option = next((o for o in options_rows if o.is_default), None)
    base_interim = interim_by_option.get(base_case_option.id) if base_case_option else None

    option_summaries: list[NzOptionSummary] = []
    for opt in options_rows:
        interim = interim_by_option.get(opt.id)
        is_base = opt.is_default
        final = None
        if not is_base and interim is not None and base_interim is not None:
            final = float(interim) - float(base_interim)

        option_summaries.append(
            NzOptionSummary(
                project_option_id=opt.id,
                option_label=opt.label,
                is_base_case=is_base,
                interim_absolute_emissions_tco2e=interim,
                final_user_emissions_tco2e=final,
            )
        )

    return NzEmissionsSummaryResponse(
        project_id=project_id,
        project_stage_instance_id=project_stage_instance_id,
        options=option_summaries,
    )

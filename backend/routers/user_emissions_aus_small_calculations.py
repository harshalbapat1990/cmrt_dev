"""
routers/user_emissions_aus_small_calculations.py

API endpoints for the AUS small-project user-emissions (B8) calculation.

Endpoints:
  POST   /api/user-emissions/aus/small/calculate
      — Run fn_veh_emissions_intensity_aus-based calculation for all
        reference-period years, store per-year results, return interim +
        final user emissions.

  GET    /api/user-emissions/aus/small/results
      — List per-year result rows for a project/stage + option.

  GET    /api/user-emissions/aus/small/summary
      — Return interim absolute + final user emissions for every option in a
        stage instance (final = option − base-case, where base-case is the
        option with is_default = true).
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from core.security import get_current_principal, Principal
from models.project_options import ProjectOption
from models.user_emissions_aus_small import UserEmissionsAusSmallResult
from schemas.user_emissions_aus_small import (
    AusSmallEmissionsCalculateRequest,
    AusSmallEmissionsCalculateResponse,
    AusSmallEmissionsSummaryResponse,
    AusSmallOptionSummary,
    UserEmissionsAusSmallResultOut,
)
from services.user_emissions_aus_small_calculations import calculate_and_store_aus_small

router = APIRouter(
    prefix="/api/user-emissions/aus/roads",
    tags=["User Emissions - AUS (B8)"],
)


# ─────────────────────────────────────────────────────────────────────────────
# POST /calculate  — run calculation, store results
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/calculate",
    response_model=AusSmallEmissionsCalculateResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate & store AUS small-project user emissions",
    description=(
        "Accepts Road Users inputs (VKT + average speed for Light, Medium, "
        "Heavy, and Super Heavy vehicle types) for one project option.  "
        "Calls fn_veh_emissions_intensity_aus for every year in the project's "
        "reference period (the state/region is resolved automatically from the "
        "project's proponent organisation; road defaults for small projects: "
        "gradient=0, curvature=20, IRI=2.0) and stores per-year results.\n\n"
        "Re-calling this endpoint with the same option overwrites previous results."
    ),
)
async def calculate_aus_small_emissions(
    payload: AusSmallEmissionsCalculateRequest,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
) -> AusSmallEmissionsCalculateResponse:
    try:
        result = await calculate_and_store_aus_small(db, payload)
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
    response_model=List[UserEmissionsAusSmallResultOut],
    summary="List per-year AUS small user-emissions results",
)
async def list_results(
    project_id: UUID = Query(...),
    project_stage_instance_id: UUID = Query(...),
    project_option_id: UUID = Query(...),
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
) -> List[UserEmissionsAusSmallResultOut]:
    rows = (
        await db.execute(
            select(UserEmissionsAusSmallResult).where(
                UserEmissionsAusSmallResult.project_id == project_id,
                UserEmissionsAusSmallResult.project_stage_instance_id == project_stage_instance_id,
                UserEmissionsAusSmallResult.project_option_id == project_option_id,
            ).order_by(UserEmissionsAusSmallResult.assessment_year)
        )
    ).scalars().all()
    return [UserEmissionsAusSmallResultOut.model_validate(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# GET /summary  — interim + final emissions for all options in a stage instance
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/summary",
    response_model=AusSmallEmissionsSummaryResponse,
    summary="Interim & final AUS small user emissions by option",
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
) -> AusSmallEmissionsSummaryResponse:
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
                UserEmissionsAusSmallResult.project_option_id,
                func.sum(UserEmissionsAusSmallResult.total_annual_emissions_tco2e).label("interim"),
            ).where(
                UserEmissionsAusSmallResult.project_id == project_id,
                UserEmissionsAusSmallResult.project_stage_instance_id == project_stage_instance_id,
            ).group_by(UserEmissionsAusSmallResult.project_option_id)
        )
    ).mappings().all()

    interim_by_option: dict[UUID, float] = {
        r["project_option_id"]: r["interim"] for r in sums_rows
    }

    # Identify base-case option
    base_case_option = next((o for o in options_rows if o.is_default), None)
    base_interim = interim_by_option.get(base_case_option.id) if base_case_option else None

    option_summaries: list[AusSmallOptionSummary] = []
    for opt in options_rows:
        interim = interim_by_option.get(opt.id)
        is_base = opt.is_default
        final = None
        if not is_base and interim is not None and base_interim is not None:
            final = float(interim) - float(base_interim)

        option_summaries.append(
            AusSmallOptionSummary(
                project_option_id=opt.id,
                option_label=opt.label,
                is_base_case=is_base,
                interim_total_emissions_tco2e=interim,
                final_user_emissions_tco2e=final,
            )
        )

    return AusSmallEmissionsSummaryResponse(
        project_id=project_id,
        project_stage_instance_id=project_stage_instance_id,
        options=option_summaries,
    )

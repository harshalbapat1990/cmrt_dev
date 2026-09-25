"""
routers/user_emissions_aus_large_road_calculations.py

API endpoints for the AUS large-project road user-emissions (B8) calculation.

Endpoints:
  POST   /api/user-emissions/aus/large/roads/calculate
      — Interpolate/extrapolate VKT + speed from anchor years, call
        fn_veh_emissions_intensity_aus for every reference-period year,
        store per-year results, return interim + final user emissions.
        One call per vehicle type.

  GET    /api/user-emissions/aus/large/roads/results
      — List per-year result rows for a project option + vehicle type.

  GET    /api/user-emissions/aus/large/roads/summary
      — Return interim absolute + final user emissions for every option in a
        stage instance (final = option − base-case).
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from core.security import get_current_principal, Principal
from models.project_options import ProjectOption
from models.user_emissions_aus_large_road import UserEmissionsAusLargeRoadResult
from schemas.user_emissions_aus_large_road import (
    AusLargeRoadCalculateRequest,
    AusLargeRoadCalculateResponse,
    AusLargeRoadOptionSummary,
    AusLargeRoadSummaryResponse,
    UserEmissionsAusLargeRoadResultOut,
)
from services.user_emissions_aus_large_road_calculations import (
    calculate_and_store_aus_large_road,
)

router = APIRouter(
    prefix="/api/user-emissions/aus/large/roads",
    tags=["User Emissions - AUS Large (B8)"],
)


# ─────────────────────────────────────────────────────────────────────────────
# POST /calculate  — interpolate, calc, store
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/calculate",
    response_model=AusLargeRoadCalculateResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate & store AUS large-project road user emissions (all vehicle types)",
    description=(
        "Accepts anchor years (user-entered modelled years with VKT and average speed) "
        "for one or more vehicle types in one project option. "
        "Each anchor year contains a 'vehicles' list so multiple vehicle types can be "
        "submitted in a single call. "
        "Interpolates between anchors and extrapolates beyond the last anchor to fill "
        "all reference-period years, then calls fn_veh_emissions_intensity_aus for "
        "each year using the supplied road parameters (gradient / curvature / roughness). "
        "Stores per-year results and returns per-vehicle annual breakdown + interim total.\n\n"
        "Re-calling with the same option overwrites previous results for the submitted vehicle types."
    ),
)
async def calculate_aus_large_road_emissions(
    payload: AusLargeRoadCalculateRequest,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
) -> AusLargeRoadCalculateResponse:
    try:
        result = await calculate_and_store_aus_large_road(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    await db.commit()
    return result


# ─────────────────────────────────────────────────────────────────────────────
# GET /results  — list per-year rows
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/results",
    response_model=List[UserEmissionsAusLargeRoadResultOut],
    status_code=status.HTTP_200_OK,
    summary="List per-year AUS large-project road results",
)
async def get_aus_large_road_results(
    project_option_id: UUID = Query(..., description="Project option ID"),
    vehicle_type: Optional[str] = Query(None, description="Filter by vehicle type"),
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
) -> List[UserEmissionsAusLargeRoadResultOut]:
    stmt = (
        select(UserEmissionsAusLargeRoadResult)
        .where(UserEmissionsAusLargeRoadResult.project_option_id == project_option_id)
        .order_by(
            UserEmissionsAusLargeRoadResult.vehicle_type,
            UserEmissionsAusLargeRoadResult.assessment_year,
        )
    )
    if vehicle_type:
        stmt = stmt.where(UserEmissionsAusLargeRoadResult.vehicle_type == vehicle_type)

    rows = (await db.execute(stmt)).scalars().all()
    return [UserEmissionsAusLargeRoadResultOut.model_validate(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# GET /summary  — interim + final totals per option in a stage
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/summary",
    response_model=AusLargeRoadSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Summary of AUS large-project road emissions per option",
)
async def get_aus_large_road_summary(
    project_stage_instance_id: UUID = Query(...),
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
) -> AusLargeRoadSummaryResponse:
    # Get all options for this stage
    opts_result = await db.execute(
        select(ProjectOption).where(
            ProjectOption.stage_instance_id == project_stage_instance_id
        )
    )
    options = opts_result.scalars().all()

    if not options:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No options found for stage instance {project_stage_instance_id}.",
        )

    # Get base-case interim total (is_default = true)
    base_case_option = next((o for o in options if o.is_default), None)
    base_case_total: Optional[float] = None

    if base_case_option:
        bc_row = (
            await db.execute(
                select(func.coalesce(func.sum(UserEmissionsAusLargeRoadResult.emissions_tco2e), 0)).where(
                    UserEmissionsAusLargeRoadResult.project_option_id == base_case_option.id
                )
            )
        ).scalar()
        base_case_total = bc_row

    summaries: list[AusLargeRoadOptionSummary] = []
    for opt in options:
        total_row = (
            await db.execute(
                select(func.coalesce(func.sum(UserEmissionsAusLargeRoadResult.emissions_tco2e), 0)).where(
                    UserEmissionsAusLargeRoadResult.project_option_id == opt.id
                )
            )
        ).scalar()

        from decimal import Decimal as _D
        interim = _D(str(total_row))
        bc      = _D(str(base_case_total)) if base_case_total is not None else None
        final   = (interim - bc) if bc is not None else None

        summaries.append(
            AusLargeRoadOptionSummary(
                project_option_id=opt.id,
                interim_total_tco2e=interim,
                base_case_emissions_tco2e=bc,
                final_user_emissions_tco2e=final,
            )
        )

    return AusLargeRoadSummaryResponse(
        project_stage_instance_id=project_stage_instance_id,
        options=summaries,
    )

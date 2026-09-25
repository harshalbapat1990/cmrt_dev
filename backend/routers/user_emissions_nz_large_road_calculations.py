"""
routers/user_emissions_nz_large_road_calculations.py

API endpoints for the NZ large-project road user-emissions (B8) calculation.

Endpoints:
  POST   /api/user-emissions/nz/large/roads/calculate
      — For one vehicle type: interpolate/extrapolate VKT + speed from user-
        supplied anchor years, look up VEPM intensity, store per-year results,
        and return interim + optional final user emissions.
        One call per vehicle type; missing types produce no rows (no error).

  GET    /api/user-emissions/nz/large/roads/results
      — List per-year result rows for a project option.
        Optionally filter by vehicle_type.

  GET    /api/user-emissions/nz/large/roads/summary
      — Return interim (and final) total emissions per option in a stage
        instance, aggregated across all vehicle types stored so far.
"""

from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import Principal, get_current_principal
from core.session import get_session
from models.project_options import ProjectOption
from models.user_emissions_nz_large_road import UserEmissionsNzLargeRoadResult
from schemas.user_emissions_nz_large_road import (
    NzLargeRoadCalculateRequest,
    NzLargeRoadCalculateResponse,
    NzLargeRoadOptionSummary,
    NzLargeRoadSummaryResponse,
    UserEmissionsNzLargeRoadResultOut,
)
from services.user_emissions_nz_large_road_calculations import (
    calculate_and_store_nz_large_road,
)

router = APIRouter(
    prefix="/api/user-emissions/nz/large/roads",
    tags=["User Emissions - NZ Large Road (B8)"],
)


# ─────────────────────────────────────────────────────────────────────────────
# POST /calculate  — run calculation, store results
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/calculate",
    response_model=NzLargeRoadCalculateResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate & store NZ large-project road user emissions",
    description=(
        "Accepts anchor-year inputs (VKT + speed) for ONE vehicle type in a large-project "
        "option.  Interpolates / extrapolates to fill all reference-period years, looks up "
        "VEPM intensity for each year, stores per-year results, and returns interim absolute "
        "emissions (tCO2e) = Σ annual emissions.\n\n"
        "Re-calling with the same option + vehicle_type overwrites previous results for that "
        "vehicle type.  Other vehicle types' stored rows are unaffected.\n\n"
        "Accepted vehicle types: general_fleet | light_vehicle | heavy_vehicle | bus"
    ),
)
async def calculate_nz_large_road_emissions(
    payload: NzLargeRoadCalculateRequest,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
) -> NzLargeRoadCalculateResponse:
    try:
        result = await calculate_and_store_nz_large_road(db, payload)
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
    response_model=List[UserEmissionsNzLargeRoadResultOut],
    summary="List per-year NZ large-road user-emissions results",
    description=(
        "Returns all stored per-year rows for a project option, ordered by "
        "vehicle_type then assessment_year.  Optionally filter to one vehicle type."
    ),
)
async def list_results(
    project_id:                UUID = Query(...),
    project_stage_instance_id: UUID = Query(...),
    project_option_id:         UUID = Query(...),
    vehicle_type:              Optional[str] = Query(None),
    db:        AsyncSession   = Depends(get_session),
    principal: Principal      = Depends(get_current_principal),
) -> List[UserEmissionsNzLargeRoadResultOut]:
    filters = [
        UserEmissionsNzLargeRoadResult.project_id == project_id,
        UserEmissionsNzLargeRoadResult.project_stage_instance_id == project_stage_instance_id,
        UserEmissionsNzLargeRoadResult.project_option_id == project_option_id,
    ]
    if vehicle_type is not None:
        filters.append(UserEmissionsNzLargeRoadResult.vehicle_type == vehicle_type)

    rows = (
        await db.execute(
            select(UserEmissionsNzLargeRoadResult)
            .where(*filters)
            .order_by(
                UserEmissionsNzLargeRoadResult.vehicle_type,
                UserEmissionsNzLargeRoadResult.assessment_year,
            )
        )
    ).scalars().all()

    return [UserEmissionsNzLargeRoadResultOut.model_validate(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# GET /summary  — interim + final emissions aggregated across all vehicle types
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/summary",
    response_model=NzLargeRoadSummaryResponse,
    summary="Interim & final NZ large-road user emissions by option",
    description=(
        "Returns total interim emissions (sum across all vehicle types) per option "
        "in a stage instance, and the final user emissions = option interim − base-case "
        "interim.  The base-case option is identified by is_default=true on project_options."
    ),
)
async def get_summary(
    project_id:                UUID = Query(...),
    project_stage_instance_id: UUID = Query(...),
    db:        AsyncSession   = Depends(get_session),
    principal: Principal      = Depends(get_current_principal),
) -> NzLargeRoadSummaryResponse:
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

    # Aggregate emissions across all vehicle types per option
    sums_rows = (
        await db.execute(
            select(
                UserEmissionsNzLargeRoadResult.project_option_id,
                func.sum(UserEmissionsNzLargeRoadResult.emissions_tco2e).label("interim"),
            ).where(
                UserEmissionsNzLargeRoadResult.project_id == project_id,
                UserEmissionsNzLargeRoadResult.project_stage_instance_id == project_stage_instance_id,
            ).group_by(UserEmissionsNzLargeRoadResult.project_option_id)
        )
    ).mappings().all()

    interim_by_option: dict[UUID, Optional[Decimal]] = {
        r["project_option_id"]: (
            Decimal(str(r["interim"])) if r["interim"] is not None else None
        )
        for r in sums_rows
    }

    # Identify base-case option (is_default=true)
    base_case_option = next((o for o in options_rows if o.is_default), None)
    base_interim = (
        interim_by_option.get(base_case_option.id) if base_case_option else None
    )

    option_summaries: list[NzLargeRoadOptionSummary] = []
    for opt in options_rows:
        interim = interim_by_option.get(opt.id)
        is_base = opt.is_default

        final: Optional[Decimal] = None
        if interim is not None and base_interim is not None and not is_base:
            final = interim - base_interim
        elif is_base and interim is not None:
            # Base case final = 0 by definition (option − base_case = itself − itself)
            final = Decimal("0")

        option_summaries.append(
            NzLargeRoadOptionSummary(
                project_option_id=opt.id,
                interim_total_tco2e=interim,
                base_case_emissions_tco2e=base_interim if not is_base else None,
                final_user_emissions_tco2e=final,
            )
        )

    return NzLargeRoadSummaryResponse(
        project_stage_instance_id=project_stage_instance_id,
        options=option_summaries,
    )

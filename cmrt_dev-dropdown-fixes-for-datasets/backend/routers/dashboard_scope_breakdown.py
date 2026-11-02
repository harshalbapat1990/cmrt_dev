from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from services._calc_utils import DashboardBase
from services.project_context_helper import ProjectContextHelper
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from services.emissions_result_aggregates import aggregate_emissions_results

router = APIRouter(
    prefix="/api/dashboard/scope-breakdown",
    tags=["Dashboard - Scope Breakdown"],
)


class ScopeBreakdownRow(DashboardBase):
    scope: str
    baseline_construction: Decimal
    baseline_operations: Decimal
    baseline_lifecycle: Decimal
    actual_construction: Decimal
    actual_operations: Decimal
    actual_lifecycle: Decimal


class ScopeBreakdownResponse(DashboardBase):
    rows: List[ScopeBreakdownRow]


# Scope totals are aggregated from structured emissions_results facts.

@router.get(
    "",
    response_model=ScopeBreakdownResponse,
    summary="Emissions breakdown by GHG scope (1/2/3), lifecycle phase and scenario",
)
async def get_scope_breakdown(
    project_id:           UUID = Query(..., description="Project UUID"),
    stage_instance_id:    UUID = Query(..., description="Project stage instance UUID"),
    elec_method:          str  = Query("market", description="Electricity accounting: 'location' or 'market'"),
    project_option_id:    Optional[UUID] = Query(None, description="Project option UUID (optional filter)"),
    submission_period_id: Optional[UUID] = Query(None, description="Submission period UUID (optional filter)"),
    db: AsyncSession = Depends(get_session),
) -> ScopeBreakdownResponse:
    if elec_method not in ("location", "market"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="elec_method must be 'location' or 'market'",
        )

    ledger = await aggregate_emissions_results(
        db,
        project_id=project_id,
        stage_instance_id=stage_instance_id,
        project_option_id=project_option_id,
        submission_period_id=submission_period_id,
        accounting_method=elec_method,
    )
    breakdown = ledger["scope_breakdown"]

    def phase_total(scope: str, phase: str, measure: str) -> Decimal:
        return Decimal(str(breakdown.get((scope, phase, measure), Decimal(0))))

    rows = []
    for scope in ("1", "2", "3"):
        con_bl = phase_total(scope, "construction", "baseline")
        ops_bl = phase_total(scope, "operations", "baseline")
        con_ac = phase_total(scope, "construction", "actual")
        ops_ac = phase_total(scope, "operations", "actual")
        rows.append(ScopeBreakdownRow(
            scope=scope,
            baseline_construction=con_bl,
            baseline_operations=ops_bl,
            baseline_lifecycle=con_bl + ops_bl,
            actual_construction=con_ac,
            actual_operations=ops_ac,
            actual_lifecycle=con_ac + ops_ac,
        ))
    total_bl_con = sum((phase_total(s, "construction", "baseline") for s in ("1", "2", "3")), Decimal(0))
    total_bl_ops = sum((phase_total(s, "operations", "baseline") for s in ("1", "2", "3")), Decimal(0))
    total_ac_con = sum((phase_total(s, "construction", "actual") for s in ("1", "2", "3")), Decimal(0))
    total_ac_ops = sum((phase_total(s, "operations", "actual") for s in ("1", "2", "3")), Decimal(0))
    rows.append(ScopeBreakdownRow(
        scope="total",
        baseline_construction=total_bl_con,
        baseline_operations=total_bl_ops,
        baseline_lifecycle=total_bl_con + total_bl_ops,
        actual_construction=total_ac_con,
        actual_operations=total_ac_ops,
        actual_lifecycle=total_ac_con + total_ac_ops,
    ))

    return ScopeBreakdownResponse(rows=rows)

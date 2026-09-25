"""
routers/org_dashboard_user_emissions.py

Organisational Dashboard — User Emissions (B8)

Aggregates road and rail user emissions data across all projects belonging to
the given organisation, with optional filters by project class, program name,
and submission stage.

One endpoint:
  GET /api/org-dashboard/user-emissions/detail  — per-project, per-year breakdown

Sources (from activity_data):
  roadUsers       → Small road user emissions per assessment year
  largeRoadUsers  → Large road user emissions per assessment year
  largeRoadParams → Large road parameter results per assessment year
  railUsers       → Small rail user emissions per assessment year
  largeRailUsers  → Large rail user emissions per assessment year

The `total_emissions_tco2e` stored in extra_fields for each row is the
pre-calculated annual result, exactly as used in the project-level B8
emissions module and the carbon valuation endpoint.

Query params
------------
  org_id         UUID   required
  project_class  str    optional  (e.g. "SMALL", "LARGE")
  program_name   str    optional
  stage          str    optional  (e.g. "CONSTRUCTION", "RECURRING")
"""

from decimal import Decimal
import re
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from services._calc_utils import DashboardBase
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session

router = APIRouter(
    prefix="/api/org-dashboard/user-emissions",
    tags=["Org Dashboard - User Emissions (B8)"],
)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class OrgUserEmissionsDetailRow(DashboardBase):
    """Per-project, per-assessment-year user emissions row."""
    project_id: UUID
    project_name: str
    stage_type: str
    assessment_year: Optional[int]
    road_emissions_tco2e: Decimal   # roadUsers + largeRoadUsers + largeRoadParams
    rail_emissions_tco2e: Decimal   # railUsers + largeRailUsers
    total_emissions_tco2e: Decimal  # road + rail combined


class OrgUserEmissionsDetailResponse(DashboardBase):
    rows: List[OrgUserEmissionsDetailRow]
    total_road_tco2e: Decimal
    total_rail_tco2e: Decimal
    total_tco2e: Decimal
    options: List[dict] = []


# ---------------------------------------------------------------------------
# Bind-params helper
# ---------------------------------------------------------------------------

def _bind(
    org_id: UUID,
    project_class: Optional[str] = None,
    program_name: Optional[str] = None,
    stage: Optional[str] = None,
    project_type_id: Optional[UUID] = None,
    project_typecast_id: Optional[UUID] = None,
) -> dict:
    return {
        "org_id": str(org_id),
        "project_class": project_class,
        "program_name": program_name,
        "stage": stage,
        "project_type_id": str(project_type_id) if project_type_id else None,
        "project_typecast_id": str(project_typecast_id) if project_typecast_id else None,
        "project_option_id": None,
        "submission_period_id": None,
    }


def _normalize_enum_filter(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", value.strip()).strip("_").upper()
    return normalized or None


def _normalize_project_class(value: Optional[str]) -> Optional[str]:
    normalized = _normalize_enum_filter(value)
    if normalized in {"SMALL", "LARGE", "RECURRING"}:
        return normalized
    return value.strip() if value else None


def _normalize_stage(value: Optional[str]) -> Optional[str]:
    normalized = _normalize_enum_filter(value)
    if normalized in {"BUSINESS_CASE", "DESIGN", "CONSTRUCTION", "RECURRING"}:
        return normalized
    return value.strip() if value else None


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

_DETAIL_SQL = text("""
WITH eligible_projects AS (
    SELECT DISTINCT
        p.id            AS project_id,
        p.project_name  AS project_name,
        psi.id          AS stage_instance_id,
        psi.stage::text AS stage_type
    FROM project p
    JOIN project_stage_instances psi ON psi.project_id = p.id
    WHERE p.is_active = TRUE
      AND (
          p.proponent_org_id = :org_id
          OR EXISTS (
              SELECT 1 FROM project_organizations po
              WHERE po.project_id    = p.id
                AND po.organization_id = :org_id
          )
      )
      AND (CAST(:project_class AS TEXT) IS NULL OR p.project_class::text = CAST(:project_class AS TEXT))
      AND (CAST(:program_name  AS TEXT) IS NULL OR LOWER(p.program_name) = LOWER(CAST(:program_name AS TEXT)))
      AND (CAST(:stage         AS TEXT) IS NULL OR psi.stage::text        = CAST(:stage         AS TEXT))
      AND (CAST(:project_type_id AS uuid) IS NULL OR p.project_type_id = CAST(:project_type_id AS uuid))
    AND (CAST(:project_typecast_id AS uuid) IS NULL OR p.project_typecast_id = CAST(:project_typecast_id AS uuid))
)

SELECT
    ep.project_id,
    ep.project_name,
    ep.stage_type,
    COALESCE(
        NULLIF(NULLIF(ad.extra_fields->>'assessment_year', ''), '-')::int,
        NULLIF(ad.extra_fields->>'year',            '')::int
    )                                                                               AS assessment_year,
    SUM(
        CASE
            WHEN ad.ui_table_key IN ('roadUsers', 'largeRoadUsers', 'largeRoadParams')
            THEN COALESCE(NULLIF(NULLIF(ad.extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)
            ELSE 0
        END
    )                                                                               AS road_emissions_tco2e,
    SUM(
        CASE
            WHEN ad.ui_table_key IN ('railUsers', 'largeRailUsers')
            THEN COALESCE(NULLIF(NULLIF(ad.extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)
            ELSE 0
        END
    )                                                                               AS rail_emissions_tco2e,
    SUM(
        COALESCE(NULLIF(NULLIF(ad.extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)
    )                                                                               AS total_emissions_tco2e
FROM activity_data ad
JOIN eligible_projects ep
    ON  ep.project_id        = ad.project_id
    AND ep.stage_instance_id = ad.project_stage_instance_id
WHERE ad.ui_table_key IN (
    'roadUsers', 'railUsers',
    'largeRoadUsers', 'largeRoadParams', 'largeRailUsers'
)
  AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
  AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
GROUP BY
    ep.project_id,
    ep.project_name,
    ep.stage_type,
    COALESCE(
        NULLIF(NULLIF(ad.extra_fields->>'assessment_year', ''), '-')::int,
        NULLIF(ad.extra_fields->>'year',            '')::int
    )
ORDER BY
    ep.project_name,
    assessment_year NULLS LAST
""")


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get(
    "/detail",
    response_model=OrgUserEmissionsDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Org User Emissions (B8) detail — per-project, per-year breakdown",
    description=(
        "Returns per-project, per-assessment-year user emissions (road + rail) "
        "across all projects in the organisation.\n\n"
        "Road sources: `roadUsers`, `largeRoadUsers`, `largeRoadParams`\n"
        "Rail sources: `railUsers`, `largeRailUsers`\n\n"
        "Each row aggregates all vehicle types for a given project and year."
    ),
)
async def org_user_emissions_detail(
    org_id: UUID = Query(..., description="Organisation UUID"),
    project_class: Optional[str] = Query(None, description="Filter by project class (e.g. SMALL, LARGE)"),
    program_name: Optional[str] = Query(None, description="Filter by program name (case-insensitive)"),
    stage: Optional[str] = Query(None, description="Filter by stage type (e.g. CONSTRUCTION, RECURRING)"),
    project_type_id: Optional[UUID] = Query(None, description="Filter by project type (benchmark mastertype UUID)"),
    project_typecast: Optional[UUID] = Query(None, description="Filter by project typecast UUID"),
    db: AsyncSession = Depends(get_session),
) -> OrgUserEmissionsDetailResponse:
    params = _bind(
        org_id,
        project_class=_normalize_project_class(project_class),
        program_name=program_name,
        stage=_normalize_stage(stage),
        project_type_id=project_type_id,
        project_typecast_id=project_typecast,
    )
    try:
        result = await db.execute(_DETAIL_SQL, params)
        rows = result.mappings().all()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {exc}",
        ) from exc

    detail_rows = [OrgUserEmissionsDetailRow(**dict(r)) for r in rows]
    total_road = sum((r.road_emissions_tco2e for r in detail_rows), Decimal(0))
    total_rail = sum((r.rail_emissions_tco2e for r in detail_rows), Decimal(0))
    total = sum((r.total_emissions_tco2e for r in detail_rows), Decimal(0))

    grouped: Dict[str, List[OrgUserEmissionsDetailRow]] = {}
    for row in detail_rows:
        grouped.setdefault(row.project_name, []).append(row)

    options: List[dict] = []
    for project_name, project_rows in grouped.items():
        by_year = {r.assessment_year: r for r in project_rows if r.assessment_year is not None}
        years = sorted(by_year.keys())

        road_values = [by_year[y].road_emissions_tco2e for y in years]
        rail_values = [by_year[y].rail_emissions_tco2e for y in years]

        options.append(
            {
                "option_label": project_name,
                "road_section": {
                    "years": years,
                    "rows": [
                        {
                            "label": "Road emissions (tCO2e)",
                            "values": road_values,
                        }
                    ],
                },
                "rail_section": {
                    "years": years,
                    "rows": [
                        {
                            "label": "Rail emissions (tCO2e)",
                            "values": rail_values,
                        }
                    ],
                },
            }
        )

    return OrgUserEmissionsDetailResponse(
        rows=detail_rows,
        total_road_tco2e=total_road,
        total_rail_tco2e=total_rail,
        total_tco2e=total,
        options=options,
    )

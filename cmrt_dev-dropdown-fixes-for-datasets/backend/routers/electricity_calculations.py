"""
routers/electricity_calculations.py

Utility endpoints for electricity grid context (jurisdiction + grid region)
derived from a project's postcodes.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from core.session import get_session
from models.postcode import ProjectPostcode
from models.jurisdictions import Jurisdiction

router = APIRouter(
    prefix="/api/electricity-calculations",
    tags=["Construction Emissions Calculations - Electricity Grid Context"],
)

# ---------------------------------------------------------------------------
# AU postcode → grid region name
# ---------------------------------------------------------------------------

def _au_postcode_to_region(postcode_str: str) -> str | None:
    """
    Map a 4-digit Australian postcode to the matching NEM/WA/NT grid region name.
    Returns None when the postcode doesn't fit any known AU range.
    """
    try:
        pc = int(postcode_str.strip())
    except (ValueError, AttributeError):
        return None

    if (1000 <= pc <= 2599) or (2619 <= pc <= 2899) or (2921 <= pc <= 2999):
        return "New South Wales"
    if (200 <= pc <= 299) or (2600 <= pc <= 2618) or (2900 <= pc <= 2920):
        return "Australian Capital Territory"
    if (3000 <= pc <= 3999) or (8000 <= pc <= 8999):
        return "Victoria"
    if (4000 <= pc <= 4999) or (9000 <= pc <= 9999):
        return "Queensland"
    if 5000 <= pc <= 5999:
        return "South Australia"
    if 6000 <= pc <= 6999:
        return "Western Australia"
    if 7000 <= pc <= 7999:
        return "Tasmania"
    if 800 <= pc <= 899:
        return "Northern Territory"
    return None


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------

class GridContextResponse(BaseModel):
    jurisdiction: str
    region: str


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get(
    "/project-grid-context/{project_id}",
    response_model=GridContextResponse,
    status_code=status.HTTP_200_OK,
    summary="Resolve electricity grid jurisdiction and region for a project",
    description=(
        "Looks up the first postcode attached to the project and maps it to "
        "an Australian NEM/WA/NT grid region. Falls back to "
        "'New South Wales' when no postcode is found or the postcode does not "
        "match any known Australian range."
    ),
)
async def get_project_grid_context(
    project_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> GridContextResponse:
    result = await db.execute(
        select(ProjectPostcode)
        .options(joinedload(ProjectPostcode.jurisdiction))
        .where(ProjectPostcode.project_id == project_id)
        .order_by(ProjectPostcode.created_on)
        .limit(1)
    )
    row = result.scalars().first()

    if row and row.jurisdiction and "new zealand" in row.jurisdiction.name.lower():
        return GridContextResponse(
            jurisdiction="New Zealand",
            region="New Zealand",
        )

    postcode_str = row.postcode if row else None
    region = _au_postcode_to_region(postcode_str) if postcode_str else None

    return GridContextResponse(
        jurisdiction="Australia",
        region=region or "New South Wales",
    )

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from schemas.project_parties import ProjectPartyOut
from crud.project_parties import list_project_parties, get_project_party

router = APIRouter(prefix="/api/project-parties", tags=["project-parties"])


@router.get("", response_model=List[ProjectPartyOut])
async def get_project_parties(
    skip: int = 0,
    limit: int = Query(50, ge=1, le=500),
    project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
    organization_id: Optional[UUID] = Query(None, description="Filter by organization ID"),
    joint_venture_id: Optional[UUID] = Query(None, description="Filter by joint venture ID"),
    db: AsyncSession = Depends(get_session),
):
    """
    Get all project parties with pagination and optional filters.
    
    - **skip**: Number of records to skip
    - **limit**: Number of records to return
    - **project_id**: Filter by project
    - **organization_id**: Filter by organization
    - **joint_venture_id**: Filter by joint venture
    """
    parties = await list_project_parties(
        db, skip, limit, project_id, organization_id, joint_venture_id
    )
    return parties


@router.get("/{party_id}", response_model=ProjectPartyOut)
async def get_project_party_by_id(
    party_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    """Get single project party by ID"""
    party = await get_project_party(db, party_id)
    if not party:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project party not found"
        )
    return party
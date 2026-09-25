from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from schemas.joint_venture_members import JointVentureMemberOut
from crud.joint_venture_members import (
    list_joint_venture_members,
    get_joint_venture_member
)

router = APIRouter(prefix="/api/joint-venture-members", tags=["joint-venture-members"])


@router.get("", response_model=List[JointVentureMemberOut])
async def get_joint_venture_members(
    skip: int = 0,
    limit: int = Query(50, ge=1, le=500),
    joint_venture_id: Optional[UUID] = Query(None, description="Filter by joint venture ID"),
    organization_id: Optional[UUID] = Query(None, description="Filter by organization ID"),
    db: AsyncSession = Depends(get_session),
):
    """
    Get all joint venture members with pagination and optional filters.
    
    - **skip**: Number of records to skip
    - **limit**: Number of records to return
    - **joint_venture_id**: Filter by joint venture
    - **organization_id**: Filter by organization
    """
    members = await list_joint_venture_members(
        db, skip, limit, joint_venture_id, organization_id
    )
    return members


@router.get("/{member_id}", response_model=JointVentureMemberOut)
async def get_joint_venture_member_by_id(
    member_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    """Get single joint venture member by ID"""
    member = await get_joint_venture_member(db, member_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Joint venture member not found"
        )
    return member
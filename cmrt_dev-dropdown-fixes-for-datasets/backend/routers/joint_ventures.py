from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from schemas.joint_ventures import JointVentureOut
from crud.joint_ventures import list_joint_ventures, get_joint_venture

router = APIRouter(prefix="/api/joint-ventures", tags=["joint-ventures"])


@router.get("", response_model=List[JointVentureOut])
async def get_joint_ventures(
    skip: int = 0,
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_session),
):
    """
    Get all joint ventures with pagination.
    
    - **skip**: Number of records to skip (default: 0)
    - **limit**: Number of records to return (default: 50, max: 500)
    """
    joint_ventures = await list_joint_ventures(db, skip, limit)
    return joint_ventures


@router.get("/{joint_venture_id}", response_model=JointVentureOut)
async def get_joint_venture_by_id(
    joint_venture_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    """Get single joint venture by ID"""
    joint_venture = await get_joint_venture(db, joint_venture_id)
    if not joint_venture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Joint venture not found"
        )
    return joint_venture
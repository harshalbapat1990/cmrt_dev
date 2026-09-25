from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from schemas.ghg_scopes import GhgScopeOut
from crud.ghg_scopes import get_ghg_scope, list_ghg_scopes

router = APIRouter(prefix="/api/ghg-scopes", tags=["ghg-scopes"])


@router.get("", response_model=List[GhgScopeOut])
async def get_all_ghg_scopes(db: AsyncSession = Depends(get_session)):
    return await list_ghg_scopes(db)


@router.get("/{scope_id}", response_model=GhgScopeOut)
async def get_ghg_scope_by_id(scope_id: int, db: AsyncSession = Depends(get_session)):
    obj = await get_ghg_scope(db, scope_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GHG scope not found")
    return obj

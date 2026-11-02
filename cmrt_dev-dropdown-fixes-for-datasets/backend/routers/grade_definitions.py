from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from schemas.grade_definitions import GradeDefinitionCreate, GradeDefinitionOut, GradeDefinitionUpdate
from crud.grade_definitions import (
    create_grade_definition,
    get_grade_definition,
    list_grade_definitions,
    update_grade_definition,
    delete_grade_definition,
)

router = APIRouter(prefix="/api/grade-definitions", tags=["grade-definitions"])


@router.post("", response_model=GradeDefinitionOut, status_code=status.HTTP_201_CREATED)
async def create_new_grade_definition(
    payload: GradeDefinitionCreate, db: AsyncSession = Depends(get_session)
):
    existing = await get_grade_definition(db, payload.id)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Grade definition id already exists")
    obj = await create_grade_definition(db, payload)
    await db.commit()
    return obj


@router.get("", response_model=List[GradeDefinitionOut])
async def get_grade_definitions(db: AsyncSession = Depends(get_session)):
    return await list_grade_definitions(db)


@router.get("/{grade_id}", response_model=GradeDefinitionOut)
async def get_grade_definition_by_id(grade_id: int, db: AsyncSession = Depends(get_session)):
    obj = await get_grade_definition(db, grade_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grade definition not found")
    return obj


@router.patch("/{grade_id}", response_model=GradeDefinitionOut)
async def patch_grade_definition(
    grade_id: int, payload: GradeDefinitionUpdate, db: AsyncSession = Depends(get_session)
):
    obj = await get_grade_definition(db, grade_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grade definition not found")
    obj = await update_grade_definition(db, obj, payload)
    await db.commit()
    return obj


@router.delete("/{grade_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_grade_definition(grade_id: int, db: AsyncSession = Depends(get_session)):
    ok = await delete_grade_definition(db, grade_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grade definition not found")
    await db.commit()
    return None

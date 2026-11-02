from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from schemas.users import UserOut, UserCreate, UserUpdate
from crud.users import create_user, get_user, get_user_by_email, list_users, update_user, delete_user

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_new_user(payload: UserCreate, db: AsyncSession = Depends(get_session)):
    existing = await get_user_by_email(db, payload.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    obj = await create_user(db, payload)
    await db.commit()
    return obj


@router.get("", response_model=List[UserOut])
async def get_users(skip: int = 0, limit: int = 50, is_active: Optional[bool] = None, db: AsyncSession = Depends(get_session)):
    objs = await list_users(db, skip, limit, is_active)
    return objs


@router.get("/{user_id:uuid}", response_model=UserOut)
async def get_user_by_id(user_id: UUID, db: AsyncSession = Depends(get_session)):
    obj = await get_user(db, user_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return obj


@router.patch("/{user_id:uuid}", response_model=UserOut)
async def patch_user(user_id: UUID, payload: UserUpdate, db: AsyncSession = Depends(get_session)):
    obj = await get_user(db, user_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if payload.email:
        existing = await get_user_by_email(db, payload.email)
        if existing and existing.id != user_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")
    obj = await update_user(db, obj, payload)
    await db.commit()
    return obj


@router.delete("/{user_id:uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user(user_id: UUID, db: AsyncSession = Depends(get_session)):
    ok = await delete_user(db, user_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await db.commit()
    return None

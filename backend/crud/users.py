from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.users import User
from schemas.users import UserCreate, UserUpdate

async def create_user(db: AsyncSession, payload: UserCreate) -> User:
    user_data = payload.model_dump()
    obj = User(**user_data)
    db.add(obj)
    await db.flush()
    return obj


async def get_user(db: AsyncSession, user_id: UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()


async def list_users(db: AsyncSession, skip: int = 0, limit: int = 50, is_active: bool | None = None) -> list[User]:
    query = select(User)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def update_user(db: AsyncSession, obj: User, payload: UserUpdate) -> User:
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(obj, key, value)
    db.add(obj)
    await db.flush()
    return obj


async def delete_user(db: AsyncSession, user_id: UUID) -> bool:
    obj = await get_user(db, user_id)
    if obj:
        await db.delete(obj)
        return True
    return False

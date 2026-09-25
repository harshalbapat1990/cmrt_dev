from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.roles import Role
from schemas.roles import RoleCreate, RoleUpdate


async def create_role(db: AsyncSession, payload: RoleCreate) -> Role:
    obj = Role(**payload.dict())
    db.add(obj)   
    await db.flush()
    await db.refresh(obj)
    return obj



async def get_role(db: AsyncSession, role_id: UUID) -> Role | None:
    result = await db.execute(select(Role).where(Role.id == role_id))
    return result.scalars().first()


async def get_role_by_name(db: AsyncSession, name: str) -> Role | None:
    result = await db.execute(select(Role).where(Role.name == name))
    return result.scalars().first()


async def list_roles(db: AsyncSession, skip: int = 0, limit: int = 50, is_active: bool | None = None) -> list[Role]:
    query = select(Role)
    if is_active is not None:
        query = query.where(Role.is_active == is_active)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def update_role(db: AsyncSession, obj: Role, payload: RoleUpdate) -> Role:
    for key, value in payload.dict(exclude_unset=True).items():
        setattr(obj, key, value)
    db.add(obj)
    return obj


async def delete_role(db: AsyncSession, role_id: UUID) -> bool:
    obj = await get_role(db, role_id)
    if obj:
        await db.delete(obj)
        return True
    return False

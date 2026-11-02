# Concrete mix CRUD functions were removed in migration dr01_drop_concrete_mix_tables.
# Data is now stored in activity_data (ui_table_key = 'concreteRegSimplified' |
# 'concreteRegDetailed'). Use crud.activity_data functions instead.

    db: AsyncSession,
    project_id: uuid.UUID,
    method: Optional[str] = None,
) -> List[ConcreteMix]:
    stmt = (
        select(ConcreteMix)
        .where(ConcreteMix.project_id == project_id)
        .order_by(ConcreteMix.sort_order, ConcreteMix.created_on)
    )
    if method:
        stmt = stmt.where(ConcreteMix.method == method)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_mix(db: AsyncSession, mix_id: uuid.UUID) -> Optional[ConcreteMix]:
    result = await db.execute(select(ConcreteMix).where(ConcreteMix.id == mix_id))
    return result.scalar_one_or_none()


async def create_mix(db: AsyncSession, payload: ConcreteMixCreate) -> ConcreteMix:
    obj = ConcreteMix(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def update_mix(
    db: AsyncSession, mix: ConcreteMix, payload: ConcreteMixUpdate
) -> ConcreteMix:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(mix, field, value)
    mix.updated_on = datetime.utcnow()
    await db.flush()
    await db.refresh(mix)
    return mix


async def delete_mix(db: AsyncSession, mix: ConcreteMix) -> None:
    await db.delete(mix)
    await db.flush()


async def list_materials(
    db: AsyncSession, concrete_mix_id: uuid.UUID
) -> List[ConcreteMixMaterial]:
    stmt = (
        select(ConcreteMixMaterial)
        .where(ConcreteMixMaterial.concrete_mix_id == concrete_mix_id)
        .order_by(ConcreteMixMaterial.sort_order, ConcreteMixMaterial.created_on)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_material(
    db: AsyncSession, material_id: uuid.UUID
) -> Optional[ConcreteMixMaterial]:
    result = await db.execute(
        select(ConcreteMixMaterial).where(ConcreteMixMaterial.id == material_id)
    )
    return result.scalar_one_or_none()


async def create_material(
    db: AsyncSession, payload: ConcreteMixMaterialCreate
) -> ConcreteMixMaterial:
    obj = ConcreteMixMaterial(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def update_material(
    db: AsyncSession,
    material: ConcreteMixMaterial,
    payload: ConcreteMixMaterialUpdate,
) -> ConcreteMixMaterial:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(material, field, value)
    material.updated_on = datetime.utcnow()
    await db.flush()
    await db.refresh(material)
    return material


async def delete_material(db: AsyncSession, material: ConcreteMixMaterial) -> None:
    await db.delete(material)
    await db.flush()

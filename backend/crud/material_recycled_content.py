from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.material_recycled_content import MaterialRecycledContent
from models.materials import Material
from models.jurisdictions import Jurisdiction
from models.background_grade_metrics import BackgroundGradeMetric
from schemas.material_recycled_content import MaterialRecycledContentCreate, MaterialRecycledContentUpdate


async def get_material_recycled_content_by_jurisdiction_and_material(
    db: AsyncSession, jurisdiction_id: Optional[UUID], material_id: Optional[UUID]
) -> Optional[MaterialRecycledContent]:
    if jurisdiction_id is None or material_id is None:
        return None
    result = await db.execute(
        select(MaterialRecycledContent).where(
            MaterialRecycledContent.jurisdiction_id == jurisdiction_id,
            MaterialRecycledContent.material_id == material_id,
            MaterialRecycledContent.is_active.is_(True),
        )
    )
    return result.scalars().first()


async def create_material_recycled_content(
    db: AsyncSession, payload: MaterialRecycledContentCreate
) -> MaterialRecycledContent:
    obj = MaterialRecycledContent(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_material_recycled_content(
    db: AsyncSession, record_id: UUID
) -> Optional[MaterialRecycledContent]:
    result = await db.execute(
        select(MaterialRecycledContent).where(MaterialRecycledContent.id == record_id)
    )
    return result.scalars().first()


async def list_material_recycled_contents(
    db: AsyncSession,
    material_id: Optional[UUID] = None,
    jurisdiction_id: Optional[UUID] = None,
    as_of_date: Optional[date] = None,
    dataset_revision_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[MaterialRecycledContent]:
    q = select(MaterialRecycledContent).where(MaterialRecycledContent.is_active.is_(True))
    if material_id is not None:
        q = q.where(MaterialRecycledContent.material_id == material_id)
    if jurisdiction_id is not None:
        q = q.where(MaterialRecycledContent.jurisdiction_id == jurisdiction_id)
    if dataset_revision_id is not None:
        q = q.where(MaterialRecycledContent.dataset_revision_id == dataset_revision_id)
    if as_of_date is not None:
        q = q.where(
            (MaterialRecycledContent.effective_from.is_(None))
            | (MaterialRecycledContent.effective_from <= as_of_date)
        ).where(
            (MaterialRecycledContent.effective_to.is_(None))
            | (MaterialRecycledContent.effective_to >= as_of_date)
        )
    result = await db.execute(q.offset(skip).limit(limit))
    return result.scalars().all()


async def list_material_recycled_contents_with_names(
    db: AsyncSession,
    material_id: Optional[UUID] = None,
    jurisdiction_id: Optional[UUID] = None,
    as_of_date: Optional[date] = None,
    dataset_revision_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    q = (
        select(
            MaterialRecycledContent,
            Material.name.label("material_name"),
            Jurisdiction.name.label("jurisdiction_name"),
        )
        .outerjoin(Material, MaterialRecycledContent.material_id == Material.id)
        .outerjoin(Jurisdiction, MaterialRecycledContent.jurisdiction_id == Jurisdiction.id)
        .where(MaterialRecycledContent.is_active.is_(True))
    )
    if material_id is not None:
        q = q.where(MaterialRecycledContent.material_id == material_id)
    if jurisdiction_id is not None:
        q = q.where(MaterialRecycledContent.jurisdiction_id == jurisdiction_id)
    if dataset_revision_id is not None:
        q = q.where(MaterialRecycledContent.dataset_revision_id == dataset_revision_id)
    if as_of_date is not None:
        q = q.where(
            (MaterialRecycledContent.effective_from.is_(None))
            | (MaterialRecycledContent.effective_from <= as_of_date)
        ).where(
            (MaterialRecycledContent.effective_to.is_(None))
            | (MaterialRecycledContent.effective_to >= as_of_date)
        )
    result = await db.execute(q.offset(skip).limit(limit))
    rows = result.all()
    out: List[Dict[str, Any]] = []
    for row in rows:
        mrc: MaterialRecycledContent = row[0]
        out.append({
            "id": mrc.id,
            "material_id": mrc.material_id,
            "recycled_from_material_id": mrc.recycled_from_material_id,
            "percent": mrc.percent,
            "jurisdiction_id": mrc.jurisdiction_id,
            "effective_from": mrc.effective_from,
            "effective_to": mrc.effective_to,
            "notes": mrc.notes,
            "material_name": row.material_name,
            "jurisdiction_name": row.jurisdiction_name,
        })
    return out


async def update_material_recycled_content(
    db: AsyncSession, obj: MaterialRecycledContent, payload: MaterialRecycledContentUpdate
) -> MaterialRecycledContent:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_material_recycled_content(db: AsyncSession, record_id: UUID) -> bool:
    obj = await get_material_recycled_content(db, record_id)
    if not obj:
        return False
    await db.delete(obj)
    return True


async def supersede_material_recycled_content(
    db: AsyncSession,
    old_obj: MaterialRecycledContent,
    payload: dict,
) -> MaterialRecycledContent:
    old_obj.is_active = False
    db.add(old_obj)
    skip_cols = {"id", "is_active"}
    data = {
        c.name: getattr(old_obj, c.name)
        for c in MaterialRecycledContent.__table__.columns
        if c.name not in skip_cols
    }
    data.update(payload)
    new_obj = MaterialRecycledContent(**data, is_active=True)
    db.add(new_obj)
    await db.flush()
    await db.refresh(new_obj)
    return new_obj


async def get_material_recycled_content_with_names(
    db: AsyncSession, record_id: UUID
) -> Optional[Dict[str, Any]]:
    q = (
        select(
            MaterialRecycledContent,
            Material.name.label("material_name"),
            Jurisdiction.name.label("jurisdiction_name"),
        )
        .outerjoin(Material, MaterialRecycledContent.material_id == Material.id)
        .outerjoin(Jurisdiction, MaterialRecycledContent.jurisdiction_id == Jurisdiction.id)
        .where(MaterialRecycledContent.id == record_id)
    )
    result = await db.execute(q)
    row = result.first()
    if row is None:
        return None
    mrc: MaterialRecycledContent = row[0]
    return {
        "id": mrc.id,
        "material_id": mrc.material_id,
        "recycled_from_material_id": mrc.recycled_from_material_id,
        "percent": mrc.percent,
        "jurisdiction_id": mrc.jurisdiction_id,
        "effective_from": mrc.effective_from,
        "effective_to": mrc.effective_to,
        "notes": mrc.notes,
        "is_active": mrc.is_active,
        "material_name": row.material_name,
        "jurisdiction_name": row.jurisdiction_name,
    }



class BlendedEFRow:
    def __init__(
        self,
        material_id: UUID,
        recycled_from_material_id: UUID,
        percent: Decimal,
        grade_id: Optional[int],
        band_code: Optional[str],
        metric_type_code: Optional[str],
        unit_code: Optional[str],
        ef_virgin: Optional[Decimal],
        ef_recycled: Optional[Decimal],
    ):
        self.material_id = material_id
        self.recycled_from_material_id = recycled_from_material_id
        self.percent = percent
        self.grade_id = grade_id
        self.band_code = band_code
        self.metric_type_code = metric_type_code
        self.unit_code = unit_code
        self.ef_virgin = ef_virgin
        self.ef_recycled = ef_recycled
        if ef_virgin is not None and ef_recycled is not None:
            p = float(percent)
            self.ef_blended: Optional[Decimal] = Decimal(
                str(round((1 - p) * float(ef_virgin) + p * float(ef_recycled), 10))
            )
        elif ef_virgin is not None:
            self.ef_blended = ef_virgin
        elif ef_recycled is not None:
            self.ef_blended = ef_recycled
        else:
            self.ef_blended = None


async def compute_blended_ef(
    db: AsyncSession,
    material_id: UUID,
    factor_set_id: UUID,
    metric_type_code: str,
    jurisdiction_id: Optional[UUID] = None,
    as_of_date: Optional[date] = None,
) -> List[BlendedEFRow]:
    mrc_q = select(MaterialRecycledContent).where(
        MaterialRecycledContent.material_id == material_id
    )
    if jurisdiction_id is not None:
        mrc_q = mrc_q.where(MaterialRecycledContent.jurisdiction_id == jurisdiction_id)
    if as_of_date is not None:
        mrc_q = mrc_q.where(
            (MaterialRecycledContent.effective_from.is_(None))
            | (MaterialRecycledContent.effective_from <= as_of_date)
        ).where(
            (MaterialRecycledContent.effective_to.is_(None))
            | (MaterialRecycledContent.effective_to >= as_of_date)
        )
    mrc_result = await db.execute(mrc_q)
    mrc_rows = mrc_result.scalars().all()
    if not mrc_rows:
        return []

    mat_a_r = await db.execute(select(Material).where(Material.id == material_id))
    mat_a = mat_a_r.scalars().first()
    if mat_a is None:
        return []

    results: List[BlendedEFRow] = []

    for mrc in mrc_rows:
        if mrc.recycled_from_material_id is None or mrc.percent is None:
            continue

        mat_b_r = await db.execute(
            select(Material).where(Material.id == mrc.recycled_from_material_id)
        )
        mat_b = mat_b_r.scalars().first()
        if mat_b is None:
            continue

        def bgm_q(cat_id: Optional[UUID]):
            q = select(BackgroundGradeMetric).where(
                BackgroundGradeMetric.factor_set_id == factor_set_id,
                BackgroundGradeMetric.metric_type_code == metric_type_code,
            )
            if cat_id is not None:
                q = q.where(BackgroundGradeMetric.emissions_category_id == cat_id)
            return q

        ef_a_r = await db.execute(bgm_q(mat_a.emissions_category_id))
        ef_a_rows = {(r.grade_id, r.band_code): r for r in ef_a_r.scalars().all()}

        ef_b_r = await db.execute(bgm_q(mat_b.emissions_category_id))
        ef_b_rows = {(r.grade_id, r.band_code): r for r in ef_b_r.scalars().all()}

        all_keys = set(ef_a_rows.keys()) | set(ef_b_rows.keys())
        for (grade_id, band_code) in sorted(all_keys):
            row_a = ef_a_rows.get((grade_id, band_code))
            row_b = ef_b_rows.get((grade_id, band_code))
            ef_v = Decimal(str(row_a.value)) if row_a and row_a.value is not None else None
            ef_r = Decimal(str(row_b.value)) if row_b and row_b.value is not None else None
            unit = (row_a or row_b).unit_code if (row_a or row_b) else None
            results.append(BlendedEFRow(
                material_id=material_id,
                recycled_from_material_id=mrc.recycled_from_material_id,
                percent=mrc.percent,
                grade_id=grade_id,
                band_code=band_code,
                metric_type_code=metric_type_code,
                unit_code=unit,
                ef_virgin=ef_v,
                ef_recycled=ef_r,
            ))

    return results

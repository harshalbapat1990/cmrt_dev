"""CRUD helpers for the BAU Electricity and Recycling Assumptions dataset."""
from decimal import Decimal
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.electricity_recycling_assumption import ElectricityRecyclingAssumption

DEFAULT_DATASET_REVISION_ID = UUID("d1e03bea-0918-4788-9922-8c5268abadee")

METRIC_LABEL_TO_CODE: dict[str, str] = {}

METRIC_DEFINITIONS: list[tuple[str, str, int, bool]] = [
    ("onsite_renewable_construction", "On-site renewable energy use (Construction)", 10, False),
    ("offsite_renewable_construction", "Off-site renewable energy use (Construction)", 20, False),
    ("grid_electricity_construction", "Grid Electricity (Construction)", 30, True),
    ("onsite_renewable_operation", "On-site renewable energy use (Operation)", 40, False),
    ("offsite_renewable_operation", "Off-site renewable energy use (Operation)", 50, False),
    ("grid_electricity_operation", "Grid Electricity (Operation)", 60, True),
    (
        "inert_waste_concrete_plastics_glass_rubble_recycling",
        "Inert waste - Concrete/ plastics / glass / rubble (Recycling)",
        70,
        False,
    ),
    ("inert_waste_metals_recycling", "Inert waste - Metals (Recycling)", 80, False),
    ("paper_cardboard_recycling", "Paper and cardboard (Recycling)", 90, False),
    ("garden_green_recycling", "Garden and green (Recycling)", 100, False),
    ("wood_recycling", "Wood (Recycling)", 110, False),
    (
        "mixed_construction_demolition_waste_recycling",
        "Mixed construction and demolition waste (Recycling)",
        120,
        False,
    ),
]

DEFAULT_BAU_PCT_BY_JURISDICTION: dict[str, dict[str, Decimal]] = {
    "Australia": {
        "onsite_renewable_construction": Decimal("0"),
        "offsite_renewable_construction": Decimal("0"),
        "grid_electricity_construction": Decimal("1"),
        "onsite_renewable_operation": Decimal("0"),
        "offsite_renewable_operation": Decimal("0"),
        "grid_electricity_operation": Decimal("1"),
        "inert_waste_concrete_plastics_glass_rubble_recycling": Decimal("0.9"),
        "inert_waste_metals_recycling": Decimal("0.9"),
        "paper_cardboard_recycling": Decimal("0.5"),
        "garden_green_recycling": Decimal("0.51"),
        "wood_recycling": Decimal("0.45"),
        "mixed_construction_demolition_waste_recycling": Decimal("0.83"),
    },
    "New Zealand": {
        "onsite_renewable_construction": Decimal("0"),
        "offsite_renewable_construction": Decimal("0"),
        "grid_electricity_construction": Decimal("1"),
        "onsite_renewable_operation": Decimal("0"),
        "offsite_renewable_operation": Decimal("0"),
        "grid_electricity_operation": Decimal("1"),
        "inert_waste_concrete_plastics_glass_rubble_recycling": Decimal("0.9"),
        "inert_waste_metals_recycling": Decimal("0.95"),
        "paper_cardboard_recycling": Decimal("0"),
        "garden_green_recycling": Decimal("0"),
        "wood_recycling": Decimal("0.25"),
        "mixed_construction_demolition_waste_recycling": Decimal("0"),
    },
}

RENEWABLE_METRIC_CODES = frozenset(
    {
        "onsite_renewable_construction",
        "offsite_renewable_construction",
        "onsite_renewable_operation",
        "offsite_renewable_operation",
    }
)

RECYCLING_METRIC_CODES = frozenset(
    code
    for code, _, _, is_calc in METRIC_DEFINITIONS
    if not is_calc and code not in RENEWABLE_METRIC_CODES
)

for _code, _label, _, _ in METRIC_DEFINITIONS:
    METRIC_LABEL_TO_CODE[_label.strip().lower()] = _code

GRID_PAIRS: list[tuple[str, str, str]] = [
    (
        "onsite_renewable_construction",
        "offsite_renewable_construction",
        "grid_electricity_construction",
    ),
    (
        "onsite_renewable_operation",
        "offsite_renewable_operation",
        "grid_electricity_operation",
    ),
]


def _default_pct(jurisdiction_name: str, metric_code: str) -> Decimal:
    jur_defaults = DEFAULT_BAU_PCT_BY_JURISDICTION.get(jurisdiction_name, {})
    return jur_defaults.get(metric_code, Decimal("0"))


def _revision_filter(q, dataset_revision_id: Optional[UUID]):
    if dataset_revision_id is None:
        return q.where(ElectricityRecyclingAssumption.dataset_revision_id.is_(None))
    return q.where(ElectricityRecyclingAssumption.dataset_revision_id == dataset_revision_id)


async def _get_jurisdiction_map(db: AsyncSession) -> dict[str, UUID]:
    from models.jurisdictions import Jurisdiction

    res = await db.execute(
        select(Jurisdiction).where(Jurisdiction.name.in_(list(DEFAULT_BAU_PCT_BY_JURISDICTION.keys())))
    )
    return {j.name: j.id for j in res.scalars().all()}


async def list_electricity_recycling_assumptions(
    db: AsyncSession,
    dataset_revision_id: Optional[UUID] = None,
    jurisdiction_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[ElectricityRecyclingAssumption], int]:
    count_stmt = (
        select(func.count())
        .select_from(ElectricityRecyclingAssumption)
        .where(ElectricityRecyclingAssumption.is_active.is_(True))
    )
    count_stmt = _revision_filter(count_stmt, dataset_revision_id)
    if jurisdiction_id is not None:
        count_stmt = count_stmt.where(
            ElectricityRecyclingAssumption.jurisdiction_id == jurisdiction_id
        )
    total = int((await db.execute(count_stmt)).scalar() or 0)

    q = select(ElectricityRecyclingAssumption).where(
        ElectricityRecyclingAssumption.is_active.is_(True)
    )
    q = _revision_filter(q, dataset_revision_id)
    if jurisdiction_id is not None:
        q = q.where(ElectricityRecyclingAssumption.jurisdiction_id == jurisdiction_id)
    q = (
        q.order_by(
            ElectricityRecyclingAssumption.jurisdiction_id,
            ElectricityRecyclingAssumption.display_order,
            ElectricityRecyclingAssumption.metric_label,
        )
        .offset(skip)
        .limit(limit)
    )
    res = await db.execute(q)
    return list(res.scalars().unique().all()), total


async def get_electricity_recycling_assumption(
    db: AsyncSession, row_id: UUID
) -> Optional[ElectricityRecyclingAssumption]:
    res = await db.execute(
        select(ElectricityRecyclingAssumption).where(
            ElectricityRecyclingAssumption.id == row_id,
            ElectricityRecyclingAssumption.is_active.is_(True),
        )
    )
    return res.scalars().first()


async def _seed_rows_for_revision(
    db: AsyncSession,
    dataset_revision_id: Optional[UUID],
    jur_map: dict[str, UUID],
) -> None:
    for jurisdiction_name, jur_id in jur_map.items():
        for code, label, order, is_calc in METRIC_DEFINITIONS:
            db.add(
                ElectricityRecyclingAssumption(
                    dataset_revision_id=dataset_revision_id,
                    jurisdiction_id=jur_id,
                    metric_code=code,
                    metric_label=label,
                    default_bau_pct=_default_pct(jurisdiction_name, code),
                    is_calculated=is_calc,
                    display_order=order,
                )
            )
    await db.flush()


async def ensure_electricity_recycling_assumptions(
    db: AsyncSession,
    dataset_revision_id: Optional[UUID] = None,
) -> List[ElectricityRecyclingAssumption]:
    rows, _ = await list_electricity_recycling_assumptions(
        db, dataset_revision_id=dataset_revision_id, skip=0, limit=1
    )
    if rows:
        await recompute_grid_rows(db, dataset_revision_id)
        return await _all_rows_for_revision(db, dataset_revision_id)

    jur_map = await _get_jurisdiction_map(db)
    if not jur_map:
        return []

    if dataset_revision_id is not None:
        global_rows, global_total = await list_electricity_recycling_assumptions(
            db, dataset_revision_id=None, skip=0, limit=500
        )
        if global_total:
            for src in global_rows:
                db.add(
                    ElectricityRecyclingAssumption(
                        dataset_revision_id=dataset_revision_id,
                        jurisdiction_id=src.jurisdiction_id,
                        metric_code=src.metric_code,
                        metric_label=src.metric_label,
                        default_bau_pct=src.default_bau_pct,
                        is_calculated=src.is_calculated,
                        display_order=src.display_order,
                    )
                )
            await db.flush()
            await recompute_grid_rows(db, dataset_revision_id)
            return await _all_rows_for_revision(db, dataset_revision_id)

    await _seed_rows_for_revision(db, dataset_revision_id, jur_map)
    await recompute_grid_rows(db, dataset_revision_id)
    return await _all_rows_for_revision(db, dataset_revision_id)


async def _all_rows_for_revision(
    db: AsyncSession, dataset_revision_id: Optional[UUID]
) -> List[ElectricityRecyclingAssumption]:
    rows, _ = await list_electricity_recycling_assumptions(
        db, dataset_revision_id=dataset_revision_id, skip=0, limit=500
    )
    return rows


async def recompute_grid_rows(
    db: AsyncSession,
    dataset_revision_id: Optional[UUID],
    jurisdiction_id: Optional[UUID] = None,
) -> List[ElectricityRecyclingAssumption]:
    rows = await _all_rows_for_revision(db, dataset_revision_id)
    if jurisdiction_id is not None:
        rows = [r for r in rows if r.jurisdiction_id == jurisdiction_id]

    by_jur: dict[UUID, dict[str, ElectricityRecyclingAssumption]] = {}
    for row in rows:
        by_jur.setdefault(row.jurisdiction_id, {})[row.metric_code] = row

    updated: List[ElectricityRecyclingAssumption] = []
    for jur_rows in by_jur.values():
        for onsite_code, offsite_code, grid_code in GRID_PAIRS:
            onsite = jur_rows.get(onsite_code)
            offsite = jur_rows.get(offsite_code)
            grid = jur_rows.get(grid_code)
            if not grid:
                continue
            onsite_val = Decimal(str(onsite.default_bau_pct)) if onsite else Decimal("0")
            offsite_val = Decimal(str(offsite.default_bau_pct)) if offsite else Decimal("0")
            grid.default_bau_pct = max(Decimal("0"), Decimal("1") - onsite_val - offsite_val)
            db.add(grid)
            updated.append(grid)
    if updated:
        await db.flush()
    return updated


def validate_editable_value(metric_code: str, value: Decimal) -> None:
    if value < 0:
        raise ValueError("Value must be positive or zero")
    if value > 1:
        raise ValueError("Value must be less than or equal to 100%")
    if metric_code in RECYCLING_METRIC_CODES and value < 0:
        raise ValueError("Recycling values must be positive")


async def validate_renewable_pair(
    db: AsyncSession,
    row: ElectricityRecyclingAssumption,
    new_value: Decimal,
) -> None:
    if row.metric_code not in RENEWABLE_METRIC_CODES:
        return

    rows = await _all_rows_for_revision(db, row.dataset_revision_id)
    by_code = {
        r.metric_code: r
        for r in rows
        if r.jurisdiction_id == row.jurisdiction_id
    }
    onsite_code, offsite_code = None, None
    for o, f, _ in GRID_PAIRS:
        if row.metric_code in (o, f):
            onsite_code, offsite_code = o, f
            break
    if not onsite_code:
        return

    onsite_val = new_value if row.metric_code == onsite_code else Decimal(
        str(by_code.get(onsite_code).default_bau_pct if by_code.get(onsite_code) else 0)
    )
    offsite_val = new_value if row.metric_code == offsite_code else Decimal(
        str(by_code.get(offsite_code).default_bau_pct if by_code.get(offsite_code) else 0)
    )
    if onsite_val + offsite_val > Decimal("1"):
        raise ValueError(
            "On-site and off-site renewable energy values must add up to 100% or less"
        )


def resolve_metric_code(metric_code: Optional[str], metric_label: Optional[str]) -> str:
    code = (metric_code or "").strip()
    if code:
        return code
    label = (metric_label or "").strip()
    if not label:
        raise ValueError("Provide metric_code or metric_label")
    resolved = METRIC_LABEL_TO_CODE.get(label.lower())
    if not resolved:
        raise ValueError(f"Unknown metric: {label!r}")
    return resolved


async def get_assumption_by_natural_key(
    db: AsyncSession,
    dataset_revision_id: Optional[UUID],
    jurisdiction_id: UUID,
    metric_code: str,
) -> Optional[ElectricityRecyclingAssumption]:
    q = select(ElectricityRecyclingAssumption).where(
        ElectricityRecyclingAssumption.is_active.is_(True),
        ElectricityRecyclingAssumption.jurisdiction_id == jurisdiction_id,
        ElectricityRecyclingAssumption.metric_code == metric_code,
    )
    q = _revision_filter(q, dataset_revision_id)
    res = await db.execute(q)
    return res.scalars().first()


async def upsert_electricity_recycling_assumption(
    db: AsyncSession,
    dataset_revision_id: UUID,
    jurisdiction_id: UUID,
    metric_code: str,
    default_bau_pct: Decimal,
) -> Tuple[ElectricityRecyclingAssumption, List[ElectricityRecyclingAssumption]]:
    await ensure_electricity_recycling_assumptions(db, dataset_revision_id)
    obj = await get_assumption_by_natural_key(
        db, dataset_revision_id, jurisdiction_id, metric_code
    )
    if not obj:
        raise ValueError(
            f"No assumption row found for metric {metric_code!r} in the selected revision"
        )
    return await update_electricity_recycling_assumption(db, obj, default_bau_pct)


async def update_electricity_recycling_assumption(
    db: AsyncSession,
    obj: ElectricityRecyclingAssumption,
    default_bau_pct: Decimal,
) -> Tuple[ElectricityRecyclingAssumption, List[ElectricityRecyclingAssumption]]:
    if obj.is_calculated:
        raise ValueError("Calculated rows cannot be edited directly")

    validate_editable_value(obj.metric_code, default_bau_pct)
    await validate_renewable_pair(db, obj, default_bau_pct)

    obj.default_bau_pct = default_bau_pct
    db.add(obj)
    await db.flush()

    recalc = await recompute_grid_rows(
        db, obj.dataset_revision_id, jurisdiction_id=obj.jurisdiction_id
    )
    await db.refresh(obj)
    return obj, recalc


ELECTRICITY_ERA_SOURCE_MAP: dict[str, dict[str, str]] = {
    "electricity": {
        "Onsite Renewable Electricity": "onsite_renewable_construction",
        "Offsite Renewable Electricity": "offsite_renewable_construction",
        "Grid Electricity": "grid_electricity_construction",
    },
    "opEnergyElectricity": {
        "Onsite Renewable Electricity": "onsite_renewable_operation",
        "Offsite Renewable Electricity": "offsite_renewable_operation",
        "Grid Electricity": "grid_electricity_operation",
    },
}


async def load_era_bau_pcts_for_jurisdiction(
    db: AsyncSession,
    dataset_revision_id: Optional[UUID],
    jurisdiction_id: UUID,
    table_key: str,
) -> dict[str, Decimal]:
    """Return UI emission_source -> BAU fraction for electricity auto mitigation."""
    source_map = ELECTRICITY_ERA_SOURCE_MAP.get(table_key)
    if not source_map:
        return {}

    await ensure_electricity_recycling_assumptions(db, dataset_revision_id)
    rows, _ = await list_electricity_recycling_assumptions(
        db,
        dataset_revision_id=dataset_revision_id,
        jurisdiction_id=jurisdiction_id,
        skip=0,
        limit=50,
    )
    code_to_pct = {r.metric_code: Decimal(str(r.default_bau_pct)) for r in rows}
    out: dict[str, Decimal] = {}
    for src, code in source_map.items():
        pct = code_to_pct.get(code, Decimal("0"))
        if pct > 1:
            pct = pct / Decimal("100")
        out[src] = pct
    return out

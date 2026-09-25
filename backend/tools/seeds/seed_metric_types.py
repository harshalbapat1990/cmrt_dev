"""
Seed script: metric_types
Inserts the typed metric codes used across all grade benchmark CSV files.

Grade 1 CAPEX-only columns  → material_share_capex, emission_intensity_a1_a3,
                               emission_intensity_a4, emission_intensity_a5
Grade 1 functional unit CSV → same 4 codes but different units per functional unit
Grade 2 component level CSV → carbon_storage, emission_factor_a1_a3,
                               emission_factor_a4, emission_factor_a5
Grade 3 & 4 detailed CSV    → emission_factor_scope1, emission_factor_scope2,
                               emission_factor_scope3

Idempotent — uses INSERT ... ON CONFLICT (code) DO NOTHING.

Run from the backend/ directory:
    python -m tools.seeds.seed_metric_types
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from core.config import settings

METRIC_TYPES = [
    # ---- Grade 1 (CAPEX-only) ----
    {
        "code": "material_share_capex",
        "name": "Material share of CAPEX",
        "description": (
            "Fraction of total capital expenditure attributed to material procurement "
            "(dimensionless ratio / percentage). Used in Grade 1 CAPEX-only benchmarks."
        ),
    },
    # ---- Grades 1 & 2 — lifecycle emission intensity / factor ----
    {
        "code": "emission_intensity_a1_a3",
        "name": "Product stage (A1–A3) emission intensity",
        "description": (
            "Embodied carbon emission intensity for the product stage "
            "(raw material supply, transport to manufacturer, manufacturing). "
            "Units vary by grade: tCO₂e/$ material spend (G1 CAPEX), "
            "tCO₂e/functional unit (G1 FU), tCO₂e/UoM (G2 component)."
        ),
    },
    {
        "code": "emission_intensity_a4",
        "name": "Transport stage (A4) emission intensity",
        "description": (
            "Emission intensity for transport from manufacturer / supplier to site. "
            "Units vary by grade (same as A1–A3 above)."
        ),
    },
    {
        "code": "emission_intensity_a5",
        "name": "Construction stage (A5) emission intensity",
        "description": (
            "Emission intensity for on-site construction activities. "
            "Units vary by grade (same as A1–A3 above)."
        ),
    },
    # ---- Grade 2 only — carbon storage ----
    {
        "code": "carbon_storage",
        "name": "Carbon storage",
        "description": (
            "Carbon sequestered or stored in a material over its service life "
            "(tCO₂e/UoM, negative value = credit). Grade 2 component-level benchmarks."
        ),
    },
    # ---- Grades 3 & 4 — direct emissions factor by GHG scope ----
    {
        "code": "emission_factor_scope1",
        "name": "Scope 1 direct emissions factor",
        "description": (
            "Direct GHG emission factor for a fuel or activity (Scope 1). "
            "Used in Grade 3 & 4 National Greenhouse Account factors (tCO₂e/UoM)."
        ),
    },
    {
        "code": "emission_factor_scope2",
        "name": "Scope 2 indirect energy emissions factor",
        "description": (
            "Indirect GHG emission factor for purchased energy (Scope 2). "
            "Used in Grade 3 & 4 National Greenhouse Account factors (tCO₂e/UoM)."
        ),
    },
    {
        "code": "emission_factor_scope3",
        "name": "Scope 3 other indirect emissions factor",
        "description": (
            "Other indirect GHG emission factor (Scope 3, upstream/downstream). "
            "Used in Grade 3 & 4 National Greenhouse Account factors (tCO₂e/UoM)."
        ),
    },
]


async def seed() -> None:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set. Check backend/.env.local")

    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        inserted = 0
        for row in METRIC_TYPES:
            result = await conn.execute(
                text(
                    "INSERT INTO metric_types (id, code, name, description) "
                    "VALUES (gen_random_uuid(), :code, :name, :description) "
                    "ON CONFLICT (code) DO NOTHING"
                ),
                row,
            )
            inserted += result.rowcount
        print(f"[seed_metric_types] {inserted}/{len(METRIC_TYPES)} rows inserted.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())

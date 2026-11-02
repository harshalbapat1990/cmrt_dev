"""
Seed lifecycle_modules reference table.
Codes follow EN 15978 lifecycle module notation.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from core.config import settings

LIFECYCLE_MODULES: list[dict] = [
    {
        "code": "A1-A3",
        "name": "Product Stage",
        "description": "Raw material extraction, transport and manufacturing (EN 15978 A1-A3).",
    },
    {
        "code": "A4",
        "name": "Transport to Site",
        "description": "Transport of products to the building site (EN 15978 A4).",
    },
    {
        "code": "A5",
        "name": "Construction Process",
        "description": "Installation into the building / construction process (EN 15978 A5).",
    },
    {
        "code": "A1-A5",
        "name": "Full Construction Phase",
        "description": "Combined product, transport and construction phases (EN 15978 A1-A5).",
    },
    {
        "code": "B2-5",
        "name": "Use Stage",
        "description": "Maintenance, repair, replacement, refurbishment (EN 15978 B2-B5).",
    },
    {
        "code": "C2",
        "name": "Transport to Waste",
        "description": "Transport to waste processing facility (EN 15978 C2).",
    },
    {
        "code": "C3-4",
        "name": "Waste Processing and Disposal",
        "description": "Waste processing and disposal (EN 15978 C3-C4).",
    },
    {
        "code": "B1",
        "name": "Use Stage - In-Use Emissions",
        "description": "Emissions during the use phase of the asset, including refrigerant gas leakage (EN 15978 B1).",
    },
    {
        "code": "B6",
        "name": "Operational Energy Use",
        "description": "Energy use during the operational phase of the asset (EN 15978 B6).",
    },
    {
        "code": "B7",
        "name": "Operational Water Use",
        "description": "Water use during the operational phase of the asset (EN 15978 B7).",
    },
    {
        "code": "B8",
        "name": "Road and Transport User Emissions",
        "description": "Emissions from road and transport users during the use stage of the asset (EN 15978 B8).",
    },
]


async def seed() -> None:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set. Check backend/.env.local")

    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        inserted = 0
        for row in LIFECYCLE_MODULES:
            result = await conn.execute(
                text(
                    "INSERT INTO lifecycle_modules (code, name, description) "
                    "VALUES (:code, :name, :description) "
                    "ON CONFLICT (code) DO NOTHING"
                ),
                row,
            )
            inserted += result.rowcount

        print(f"[seed_lifecycle_modules] {inserted}/{len(LIFECYCLE_MODULES)} rows inserted.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())

"""
Seed: materials

Placeholder seed script — populate rows list below when authoritative data
is available, then run:
    python -m tools.seeds.run_all    (from backend/ directory)

or run this script directly:
    python -m tools.seeds.seed_materials
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from core.config import settings

# NOTE: This is a placeholder seed for materials. Populate the MATERIALS list with actual material data when available, and then run this script to insert the materials into the database. Each material should have a unique name to avoid conflicts. The category field can be used for grouping materials in the frontend and should be defined based on actual classification needs (e.g., "Construction", "Pavement", "Structural", etc.).
# Add seed rows here when data is ready.
# Format: (name, category, is_active)

MATERIALS: list[tuple] = [
    # ("Concrete", "Construction", True),
    # ("Asphalt", "Pavement", True),
    # ("Steel", "Structural", True),
]


async def seed() -> None:
    if not MATERIALS:
        print("  [materials] No seed data defined — skipping.")
        return

    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        for (name, category, is_active) in MATERIALS:
            await session.execute(
                text("""
                    INSERT INTO materials (name, category, is_active)
                    VALUES (:name, :category, :is_active)
                    ON CONFLICT (name) DO NOTHING
                """),
                {"name": name, "category": category, "is_active": is_active},
            )
        await session.commit()
    await engine.dispose()
    print(f"  [materials] Seeded {len(MATERIALS)} rows.")


if __name__ == "__main__":
    asyncio.run(seed())

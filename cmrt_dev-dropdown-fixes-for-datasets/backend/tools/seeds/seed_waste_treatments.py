"""
Seed: waste_treatments

Placeholder — populate WASTE_TREATMENTS below when authoritative data is available.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from core.config import settings

# NOTE: waste_treatments are referenced by material_recycled_content, but currently there are no assumptions tied to specific treatments, so this seed can be run independently of materials. If that changes in the future, we may want to add a material_id foreign key here and adjust the seed data accordingly.
# Add seed rows here.
# Format: (name, is_active)

WASTE_TREATMENTS: list[tuple] = [
    # ("Landfill", True),
    # ("Recycling", True),
    # ("Reuse", True),
]


async def seed() -> None:
    if not WASTE_TREATMENTS:
        print("  [waste_treatments] No seed data defined — skipping.")
        return

    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        for (name, is_active) in WASTE_TREATMENTS:
            await session.execute(
                text("""
                    INSERT INTO waste_treatments (name, is_active)
                    VALUES (:name, :is_active)
                    ON CONFLICT (name) DO NOTHING
                """),
                {"name": name, "is_active": is_active},
            )
        await session.commit()
    await engine.dispose()
    print(f"  [waste_treatments] Seeded {len(WASTE_TREATMENTS)} rows.")


if __name__ == "__main__":
    asyncio.run(seed())

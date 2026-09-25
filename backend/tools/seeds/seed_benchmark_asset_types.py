import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except ImportError:
    pass

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable not set.")
    sys.exit(1)

async_url = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://").replace(
    "postgres://", "postgresql+asyncpg://"
)

ASSET_TYPES: list[tuple[str, str, list[str]]] = [
    (
        "transport_building",
        "Transport Building",
        [
            "Parking Facility",
            "Warehouse",
        ],
    ),
    (
        "rail",
        "Rail",
        [
            "Bridge (Rail)",
            "Light Rail",
            "Light Rail Stabling and Signalling Works",
            "Main Line Works (Rail)",
            "Station (Rail)",
            "Tunnel (Rail)",
        ],
    ),
    (
        "road",
        "Road",
        [
            "Bridge (Road)",
            "Low Use Road",
            "Low Use Road Rehabilitation Maintenance",
            "Routine Road Maintenance",
            "State Road (Highway/Freeway)",
            "State Road (Highway/Freeway) Rehabilitation Maintenance",
            "Tunnel (Road)",
            "Road/Busway/Path",
            "Bridge Only",
            "Intersection Improvements",
            "Tunnel",
            "Safety and Traffic Flow Improvements",
        ],
    ),
    (
        "road_rail",
        "Road/Rail",
        [
            "Level Crossing",
        ],
    ),
]


async def seed() -> None:
    engine = create_async_engine(async_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        async with session.begin():
            mt_count = 0
            tc_count = 0

            for mt_code, mt_name, typecasts in ASSET_TYPES:
                await session.execute(
                    text(
                        """
                        INSERT INTO benchmark_mastertypes (id, code, name)
                        VALUES (gen_random_uuid(), :code, :name)
                        ON CONFLICT (code) DO NOTHING
                        """
                    ),
                    {"code": mt_code, "name": mt_name},
                )
                mt_count += 1

                result = await session.execute(
                    text("SELECT id FROM benchmark_mastertypes WHERE code = :code"),
                    {"code": mt_code},
                )
                mt_id = result.scalar_one()

                for tc_name in typecasts:
                    tc_code = (
                        tc_name.lower()
                        .replace("/", "_")
                        .replace("(", "")
                        .replace(")", "")
                        .replace(" ", "_")
                        .strip("_")
                    )
                    await session.execute(
                        text(
                            """
                            INSERT INTO benchmark_typecasts (id, code, name, mastertype_id)
                            VALUES (gen_random_uuid(), :code, :name, :mastertype_id)
                            ON CONFLICT (name, mastertype_id) DO NOTHING
                            """
                        ),
                        {"code": tc_code, "name": tc_name, "mastertype_id": str(mt_id)},
                    )
                    tc_count += 1

    await engine.dispose()
    print(f"Done. Seeded {mt_count} mastertypes, {tc_count} typecasts (ON CONFLICT DO NOTHING).")


if __name__ == "__main__":
    asyncio.run(seed())

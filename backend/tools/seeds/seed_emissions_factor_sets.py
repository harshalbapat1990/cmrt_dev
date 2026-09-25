"""
Seed script: emissions_factor_sets
NOTE: The emissions_factor_sets table was dropped in migration 9a8b7c6d5e4f
(no-factor-sets delta architecture). This seed is now a no-op.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


async def seed() -> None:
    print("[seed_emissions_factor_sets] Skipped - table was dropped in migration 9a8b7c6d5e4f.")


if __name__ == "__main__":
    asyncio.run(seed())

"""
Seed script: project_dataset_exclusions
No-op — project_dataset_exclusions rows are created through the application API
when a project explicitly excludes a specific benchmark metric from its revision.

Run from the backend/ directory:
    python -m tools.seeds.seed_project_dataset_exclusions
"""
import asyncio


async def seed() -> None:
    print(
        "[seed_project_dataset_exclusions] No-op — rows are created via the API "
        "when a project excludes a specific background_grade_metric."
    )


if __name__ == "__main__":
    asyncio.run(seed())

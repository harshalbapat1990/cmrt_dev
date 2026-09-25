"""
Seed script: project_dataset_revisions
No-op — project_dataset_revisions rows are created through the application API
when a project is linked to a dataset revision.

Run from the backend/ directory:
    python -m tools.seeds.seed_project_dataset_revisions
"""
import asyncio


async def seed() -> None:
    print(
        "[seed_project_dataset_revisions] No-op — rows are created via the API "
        "when a project is linked to a dataset revision."
    )


if __name__ == "__main__":
    asyncio.run(seed())

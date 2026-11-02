"""
Seed script: dataset_revision_changes
No-op — dataset_revision_changes rows are written by the application when a
dataset revision value is corrected and the change needs to be audited.

Run from the backend/ directory:
    python -m tools.seeds.seed_dataset_revision_changes
"""
import asyncio


async def seed() -> None:
    print(
        "[seed_dataset_revision_changes] No-op — rows are created via the API "
        "when a background_grade_metric value is corrected within a revision."
    )


if __name__ == "__main__":
    asyncio.run(seed())

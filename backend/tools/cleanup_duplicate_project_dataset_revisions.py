"""
tools/cleanup_duplicate_project_dataset_revisions.py
===================================================
One-off utility to remove duplicate project_dataset_revisions rows from the database.
For each project, only the most recently applied dataset revision (by applied_at DESC)
is retained, ensuring exactly one active dataset revision per project.

Usage (from backend/ directory):
    python -m tools.cleanup_duplicate_project_dataset_revisions
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from core.config import settings
from models.project_dataset_revisions import ProjectDatasetRevision


async def cleanup_duplicates():
    if not settings.database_url:
        print("DATABASE_URL is not configured.")
        return

    engine = create_async_engine(settings.database_url, echo=False)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as session:
        # Fetch all project_dataset_revisions ordered by project_id and applied_at DESC
        stmt = (
            select(ProjectDatasetRevision)
            .order_by(
                ProjectDatasetRevision.project_id,
                ProjectDatasetRevision.applied_at.desc(),
                ProjectDatasetRevision.id.desc(),
            )
        )
        result = await session.execute(stmt)
        all_rows = result.scalars().all()

        seen_projects = set()
        ids_to_delete = []

        for row in all_rows:
            if row.project_id in seen_projects:
                ids_to_delete.append(row.id)
                print(
                    f"Found duplicate for project {row.project_id}: "
                    f"deleting old row {row.id} (revision: {row.dataset_revision_id}, applied_at: {row.applied_at})"
                )
            else:
                seen_projects.add(row.project_id)
                print(
                    f"Keeping latest for project {row.project_id}: "
                    f"row {row.id} (revision: {row.dataset_revision_id}, applied_at: {row.applied_at})"
                )

        if ids_to_delete:
            del_stmt = delete(ProjectDatasetRevision).where(ProjectDatasetRevision.id.in_(ids_to_delete))
            await session.execute(del_stmt)
            await session.commit()
            print(f"\nSuccessfully deleted {len(ids_to_delete)} duplicate row(s).")
        else:
            print("\nNo duplicates found.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(cleanup_duplicates())

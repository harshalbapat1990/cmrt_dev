import asyncio
import sys
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from models.carbon_values import CarbonValue
from core.config import settings


async def cleanup_duplicates():
    """Remove duplicate carbon value records, keeping only the first set."""
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        from sqlalchemy.future import select
        from sqlalchemy import delete

        # Get total count
        result = await db.execute(select(CarbonValue))
        all_records = result.scalars().all()
        total = len(all_records)
        
        print(f"Total records before cleanup: {total}")
        
        if total <= 684:
            print("✓ No duplicates found")
            await engine.dispose()
            return
        
        # Delete records after the first 684 (keep first 684, delete rest)
        # Get IDs of records to delete (skip first 684, get rest)
        result = await db.execute(select(CarbonValue.id).offset(684))
        ids_to_delete = [row[0] for row in result.fetchall()]
        
        if ids_to_delete:
            await db.execute(delete(CarbonValue).where(CarbonValue.id.in_(ids_to_delete)))
            await db.commit()
            print(f"✓ Deleted {len(ids_to_delete)} duplicate records")
            
            # Verify
            result = await db.execute(select(CarbonValue))
            remaining = len(result.scalars().all())
            print(f"✓ Total records after cleanup: {remaining}")
        else:
            print("✓ No duplicates to remove")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(cleanup_duplicates())

import asyncio
import sys
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from models.carbon_values import CarbonValue
from core.config import settings


async def remove_all_duplicates():
    """Remove all duplicate records, keeping only the first of each (jurisdiction_id, range_code, year)."""
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        from sqlalchemy.future import select

        # Get total count before
        result = await db.execute(select(CarbonValue))
        all_records = result.scalars().all()
        before_count = len(all_records)
        print(f"Total records before cleanup: {before_count}")

        # Find and delete duplicates using SQL window function
        # Keep only the first (by id) record for each (jurisdiction_id, range_code, year) combination
        delete_query = text("""
            DELETE FROM carbon_values
            WHERE id IN (
                SELECT id FROM (
                    SELECT id, 
                           ROW_NUMBER() OVER (PARTITION BY jurisdiction_id, range_code, year ORDER BY id) as rn
                    FROM carbon_values
                ) t
                WHERE rn > 1
            )
        """)
        
        await db.execute(delete_query)
        await db.commit()
        
        # Verify results
        result = await db.execute(select(CarbonValue))
        remaining_records = result.scalars().all()
        after_count = len(remaining_records)
        
        deleted = before_count - after_count
        print(f"✓ Deleted {deleted} duplicate records")
        print(f"✓ Total records after cleanup: {after_count}")
        
        if deleted > 0:
            # Sample some records to verify uniqueness
            sample_query = text("""
                SELECT jurisdiction_id, range_code, year, COUNT(*) as cnt
                FROM carbon_values
                GROUP BY jurisdiction_id, range_code, year
                HAVING COUNT(*) > 1
            """)
            
            result = await db.execute(sample_query)
            dups = result.fetchall()
            if dups:
                print(f"⚠️  Found {len(dups)} still-duplicate combinations:")
                for dup in dups:
                    print(f"  - jurisdiction {dup[0]}, range {dup[1]}, year {dup[2]}: {dup[3]} records")
            else:
                print("✓ All duplicates removed - data is now unique!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(remove_all_duplicates())

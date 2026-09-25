"""
Seed script for postcode_reference table.
This script loads postal code data from CSV and seeds it into the database.
Useful as a backup if the upload endpoint fails with large files.
"""

import asyncio
import csv
import sys
from pathlib import Path
from decimal import Decimal

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.config import Settings
from models.postcode import PostcodeReference, AreaClass
from models.jurisdictions import Jurisdiction
from crud import postcode as crud_postcode

# Load database configuration
settings = Settings()
DATABASE_URL = settings.database_url

# Area mapping from CSV
AREA_CLASS_MAPPING = {
    "METROPOLITAN": AreaClass.METROPOLITAN,
    "REGIONAL": AreaClass.REGIONAL,
    "REMOTE": AreaClass.REMOTE,
    "RURAL": AreaClass.RURAL,
}

async def seed_postal_codes():
    """Load postal codes from CSV and seed into database."""
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    csv_path = Path(__file__).parent / "data" / "PostalCodes.csv"
    
    if not csv_path.exists():
        print(f" CSV file not found at {csv_path}")
        return
    
    async with async_session() as session:
        print(" Starting postal codes seeding...")
        
        # Get all jurisdictions
        jur_result = await session.execute(select(Jurisdiction))
        jurisdictions = {jur.name: jur.id for jur in jur_result.scalars().all()}
        
        if not jurisdictions:
            print(" No jurisdictions found in database. Please seed jurisdictions first.")
            return
        
        print(f" Found {len(jurisdictions)} jurisdictions: {', '.join(jurisdictions.keys())}")
        
        skipped = 0
        created = 0
        updated = 0
        errors = []
        batch_size = 500
        batch_count = 0
        
        # Use utf-8-sig to skip BOM (Byte Order Mark) character
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, start=2):  # Start at 2 because row 1 is header
                try:
                    # Strip whitespace from keys and values
                    row = {k.strip(): v.strip() if isinstance(v, str) else v for k, v in row.items()}
                    
                    jurisdiction_name = row.get("Jurisdiction", "").strip()
                    postcode = row.get("Postal code", "").strip()
                    area_raw = row.get("Final CMRT Area", "").strip().upper()
                    
                    if not jurisdiction_name or not postcode or not area_raw:
                        print(f"  Row {i}: Missing required fields")
                        skipped += 1
                        continue
                    
                    # Validate jurisdiction
                    if jurisdiction_name not in jurisdictions:
                        errors.append(f"Row {i}: Jurisdiction '{jurisdiction_name}' not found")
                        skipped += 1
                        continue
                    
                    # Validate area class
                    if area_raw not in AREA_CLASS_MAPPING:
                        errors.append(
                            f"Row {i}: Invalid area class '{area_raw}' for postcode {postcode}. "
                            f"Allowed: METROPOLITAN, REGIONAL, REMOTE, RURAL"
                        )
                        skipped += 1
                        continue
                    
                    jurisdiction_id = jurisdictions[jurisdiction_name]
                    area = AREA_CLASS_MAPPING[area_raw]
                    
                    # Upsert record
                    record, is_created = await crud_postcode.upsert_postcode_reference(
                        session, postcode, jurisdiction_id, area
                    )
                    
                    if is_created:
                        created += 1
                        if created % 100 == 0:
                            print(f"  ✓ Created {created} records...")
                    else:
                        updated += 1
                    
                    batch_count += 1
                    
                    # Commit in batches
                    if batch_count >= batch_size:
                        await session.commit()
                        batch_count = 0
                    
                except Exception as e:
                    errors.append(f"Row {i}: {str(e)}")
                    skipped += 1
        
        # Final commit for remaining records
        if batch_count > 0:
            await session.commit()
        
        print(f"\n Seeding complete:")
        print(f"   Created: {created}")
        print(f"   Updated: {updated}")
        print(f"   Total processed: {created + updated}")
        print(f"   Skipped: {skipped}")
        
        if errors:
            print(f"\n Errors encountered ({len(errors)} total):")
            for error in errors[:20]:  # Show first 20 errors
                print(f"   - {error}")
            if len(errors) > 20:
                print(f"   ... and {len(errors) - 20} more errors")
        
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_postal_codes())

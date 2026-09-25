import asyncio
import csv
from pathlib import Path
from decimal import Decimal
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from models.fugitives import Fugitive
from models.jurisdictions import Jurisdiction
from core.config import settings

# Path to CSV file
CSV_FILE = Path(__file__).parent / "data" / "Final Data" / "Fugitives.csv"


async def seed_fugitives():
    """Seed Fugitives table from CSV
    
    Records are seeded with dataset_revision_id = NULL by default (global data).
    For revision-specific data, update dataset_revision_id after initial seeding.
    """
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Build jurisdiction lookup
        from sqlalchemy.future import select

        jurisdictions_result = await db.execute(select(Jurisdiction))
        jurisdictions = {j.name: j.id for j in jurisdictions_result.scalars().all()}

        if not jurisdictions:
            print("⚠️  No jurisdictions found in database. Please seed jurisdictions first.")
            await engine.dispose()
            return

        print(f"Found {len(jurisdictions)} jurisdictions")

        # Read and seed CSV
        if not CSV_FILE.exists():
            print(f" CSV file not found: {CSV_FILE}")
            await engine.dispose()
            return
        
        with open(CSV_FILE, "r", encoding="utf-8-sig") as csvfile:
            reader = csv.DictReader(csvfile)
            count = 0
            skipped = 0
            updated = 0
            
            for row in reader:
                # Strip keys in case CSV has trailing spaces in headers
                row = {k.strip(): v for k, v in row.items()}
                
                jurisdiction_name = row.get("Jurisdiction", "").strip()
                equipment_type = row.get("Equipment type", "").strip()
                rate_str = row.get("Default annual leakage rate of gas", "").strip()
                source_comments = row.get("Source/Comments", "").strip()

                # Validate required fields
                if not jurisdiction_name or not equipment_type:
                    # print(f"  Skipping row with missing jurisdiction or equipment_type")
                    skipped += 1
                    continue

                # Parse rate (remove % sign if present)
                rate_str_clean = rate_str.rstrip("%") if rate_str.endswith("%") else rate_str
                rate = Decimal(rate_str_clean) if rate_str_clean else None

                jurisdiction_id = jurisdictions.get(jurisdiction_name)
                if not jurisdiction_id:
                    # Try to find a case-insensitive match
                    for jname, jid in jurisdictions.items():
                        if jname.lower() == jurisdiction_name.lower():
                            jurisdiction_id = jid
                            break
                    
                    if not jurisdiction_id:
                        # print(f"  Jurisdiction '{jurisdiction_name}' not found. Available: {list(jurisdictions.keys())}")
                        skipped += 1
                        continue

                # Check if record already exists (with dataset_revision_id = NULL for global records)
                from sqlalchemy.future import select
                existing = await db.execute(
                    select(Fugitive).where(
                        (Fugitive.jurisdiction_id == jurisdiction_id) &
                        (Fugitive.equipment_type == equipment_type) &
                        (Fugitive.dataset_revision_id.is_(None))
                    )
                )
                existing_record = existing.scalars().first()
                
                if existing_record:
                    # Update existing record
                    existing_record.default_annual_leakage_rate = rate
                    existing_record.source_comments = source_comments
                    updated += 1
                else:
                    # Create new Fugitive record
                    fugitive = Fugitive(
                        dataset_revision_id=None,  # Global/default data
                        jurisdiction_id=jurisdiction_id,
                        equipment_type=equipment_type,
                        default_annual_leakage_rate=rate,
                        source_comments=source_comments,
                    )
                    db.add(fugitive)
                    count += 1

            await db.commit()
            print(f" Seeded {count} new fugitive records")
            if updated:
                print(f" Updated {updated} existing fugitive records")
            if skipped:
                print(f"  Skipped {skipped} rows due to validation errors")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_fugitives())

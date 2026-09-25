import asyncio
import csv
import sys
from pathlib import Path
from decimal import Decimal
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add backend directory to Python path so imports work
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from models.carbon_value_ranges import CarbonValueRange
from models.carbon_values import CarbonValue
from models.jurisdictions import Jurisdiction
from core.config import settings

# Path to CSV file
CSV_FILE = Path(__file__).parent / "data" / "Final Data" / "Carbon Values.csv"


async def seed_carbon_values():
    """Seed CarbonValueRange and CarbonValue tables from CSV
    
    Records are seeded with dataset_revision_id = NULL by default (global data).
    For revision-specific data, update dataset_revision_id after initial seeding.
    """
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        from sqlalchemy.future import select

        # First, ensure Range lookup table is populated
        ranges = [
            CarbonValueRange(code="low", name="Low"),
            CarbonValueRange(code="central", name="Central"),
            CarbonValueRange(code="high", name="High"),
        ]
        
        for range_obj in ranges:
            existing = await db.execute(
                select(CarbonValueRange).where(CarbonValueRange.code == range_obj.code)
            )
            if not existing.scalars().first():
                db.add(range_obj)
        
        await db.commit()
        print("✓ Carbon value ranges ensured in database")

        # Check if carbon values already seeded
        cv_count_result = await db.execute(select(CarbonValue))
        existing_count = len(cv_count_result.scalars().all())
        
        if existing_count > 0:
            print(f"⚠️  Carbon values already seeded ({existing_count} records found)")
            print("To re-seed, delete existing records and run again.")
            await engine.dispose()
            return

        # Build jurisdiction lookup
        jurisdictions_result = await db.execute(select(Jurisdiction))
        jurisdictions = {j.name: j.id for j in jurisdictions_result.scalars().all()}

        if not jurisdictions:
            print("⚠️  No jurisdictions found in database. Please seed jurisdictions first.")
            await engine.dispose()
            return

        print(f"Found {len(jurisdictions)} jurisdictions")

        # Read and seed CSV
        if not CSV_FILE.exists():
            print(f"⚠️  CSV file not found: {CSV_FILE}")
            await engine.dispose()
            return
        
        # Parse all CSV data first
        carbon_values_to_insert = []
        skipped = 0
        
        with open(CSV_FILE, "r", encoding="utf-8-sig") as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                # Strip keys in case CSV has trailing spaces in headers
                row = {k.strip(): v for k, v in row.items()}
                
                jurisdiction_name = row.get("Jurisdiction", "").strip()
                range_name = row.get("Range", "").strip()
                currency = row.get("Currency", "").strip()
                source = row.get("Source/Comments", "").strip()

                # Map range name to code
                range_code_map = {
                    "Low": "low",
                    "Central": "central",
                    "High": "high",
                }
                range_code = range_code_map.get(range_name)

                # Validate required fields
                if not jurisdiction_name or not range_code:
                    skipped += 1
                    continue

                jurisdiction_id = jurisdictions.get(jurisdiction_name)
                if not jurisdiction_id:
                    # Try case-insensitive match
                    for jname, jid in jurisdictions.items():
                        if jname.lower() == jurisdiction_name.lower():
                            jurisdiction_id = jid
                            break
                    
                    if not jurisdiction_id:
                        skipped += 1
                        continue

                # Process years 2025-2100
                for year in range(2025, 2101):
                    year_str = str(year)
                    value_str = row.get(year_str, "").strip()

                    if not value_str or value_str == "—":
                        continue

                    # Clean value: remove currency symbols and commas
                    value_str_clean = (
                        value_str.replace("$", "")
                        .replace(",", "")
                        .strip()
                    )

                    try:
                        value = Decimal(value_str_clean)
                    except Exception:
                        continue

                    # Add to batch insert list
                    carbon_values_to_insert.append({
                        'dataset_revision_id': None,
                        'jurisdiction_id': jurisdiction_id,
                        'range_code': range_code,
                        'year': year,
                        'value': value,
                        'currency': currency if currency else None,
                        'source': source if source else None,
                    })

        # Bulk insert parsed data
        if carbon_values_to_insert:
            from sqlalchemy import insert
            stmt = insert(CarbonValue)
            await db.execute(stmt, carbon_values_to_insert)
            await db.commit()
            print(f"✓ Seeded {len(carbon_values_to_insert)} carbon value records")
        
        if skipped:
            print(f"⚠️  Skipped {skipped} rows due to validation errors")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_carbon_values())

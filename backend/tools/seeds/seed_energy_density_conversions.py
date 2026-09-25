import asyncio
import csv
from pathlib import Path
from decimal import Decimal
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from models.energy_density_conversions import EnergyDensityConversion
from models.units import Unit
from core.config import settings

# Path to CSV file
CSV_FILE = Path(__file__).parent / "data" / "Final Data" / "Energy Densities Conversions.csv"


async def seed_energy_density_conversions():
    """Seed EnergyDensityConversions table from CSV
    
    Records are seeded with dataset_revision_id = NULL by default (global data).
    For revision-specific data, update dataset_revision_id after initial seeding.
    """
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Build unit lookup by unit code
        from sqlalchemy.future import select

        units_result = await db.execute(select(Unit))
        units = {u.code: u.id for u in units_result.scalars().all()}

        if not units:
            print("⚠️  No units found in database. Please seed units first.")
            await engine.dispose()
            return

        print(f"Found {len(units)} units")

        # Read and seed CSV
        with open(CSV_FILE, "r", encoding="utf-8-sig") as csvfile:
            reader = csv.DictReader(csvfile)
            count = 0
            skipped = 0
            updated = 0
            
            for row in reader:
                # Strip keys in case CSV has trailing spaces in headers
                row = {k.strip(): v for k, v in row.items()}
                
                category = row.get("Fuel type", "").strip()
                name = row.get("Fuel", "").strip()
                unit_code = row.get("Unit", "").strip()
                energy_density_str = row.get("Energy content factor (GJ/unit)", "").strip()
                source_comments = row.get("Source/Comments", "").strip()

                # Validate required fields
                if not category or not name or not unit_code:
                    # print(f"⚠️  Skipping row with missing category, name, or unit")
                    skipped += 1
                    continue

                # Parse energy density
                energy_density = (
                    Decimal(energy_density_str) if energy_density_str else None
                )

                unit_id = units.get(unit_code)
                if not unit_id:
                    # Try case-insensitive match
                    for ucode, uid in units.items():
                        if ucode.lower() == unit_code.lower():
                            unit_id = uid
                            break
                    
                    if not unit_id:
                        # print(f"⚠️  Unit code '{unit_code}' not found")
                        skipped += 1
                        continue

                # Check if record already exists (with dataset_revision_id = NULL for global records)
                from sqlalchemy.future import select
                existing = await db.execute(
                    select(EnergyDensityConversion).where(
                        (EnergyDensityConversion.category == category) &
                        (EnergyDensityConversion.name == name) &
                        (EnergyDensityConversion.unit_id == unit_id) &
                        (EnergyDensityConversion.dataset_revision_id.is_(None))
                    )
                )
                existing_record = existing.scalars().first()
                
                if existing_record:
                    # Update existing record
                    existing_record.energy_density = energy_density
                    existing_record.source_comments = source_comments
                    updated += 1
                else:
                    # Create EnergyDensityConversion record
                    edc = EnergyDensityConversion(
                        dataset_revision_id=None,  # Global/default data
                        category=category,
                        name=name,
                        unit_id=unit_id,
                        energy_density=energy_density,
                        source_comments=source_comments,
                    )
                    db.add(edc)
                    count += 1

            await db.commit()
            print(f"✅ Seeded {count} new energy density conversion records")
            if updated:
                print(f"✅ Updated {updated} existing energy density conversion records")
            if skipped:
                print(f"⚠️  Skipped {skipped} rows due to validation errors or missing unit codes")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_energy_density_conversions())

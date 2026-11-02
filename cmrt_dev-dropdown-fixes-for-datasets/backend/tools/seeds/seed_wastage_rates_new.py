"""
Seed script for default_wastage_rates table.
This script loads wastage rate data from CSV and seeds it into the database.
"""

import asyncio
import csv
import sys
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.config import Settings
from models.default_wastage_rate import DefaultWastageRate
from models.materials import Material
from models.jurisdictions import Jurisdiction
from crud.default_wastage_rate import create_wastage_rate
from schemas.default_wastage_rate import DefaultWastageRateCreate

# Load database configuration
settings = Settings()
DATABASE_URL = settings.database_url


async def seed_wastage_rates():
    """Load and seed wastage rates from CSV."""
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    csv_path = Path(__file__).parent / "data" / "Final Data" / "Wastage and EoL.csv"
    
    if not csv_path.exists():
        print(f"❌ CSV file not found: {csv_path}")
        await engine.dispose()
        return
    
    async with async_session() as session:
        try:
            # Get jurisdiction and material mappings
            jurisdictions_query = await session.execute(
                text("SELECT id, name FROM jurisdictions")
            )
            jurisdictions = {row[1]: row[0] for row in jurisdictions_query}
            
            materials_query = await session.execute(
                text("SELECT id, name FROM materials")
            )
            materials = {row[1]: row[0] for row in materials_query}
            
            print(f"✓ Found {len(jurisdictions)} jurisdictions")
            print(f"✓ Found {len(materials)} materials")
            
            skipped = 0
            created = 0
            errors = []
            
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader, start=2):  # Start at 2 because row 1 is header
                    try:
                        # Strip whitespace from keys
                        row = {k.strip(): v for k, v in row.items()}
                        
                        jurisdiction_name = row.get("Jurisdiction", "").strip()
                        material_name = row.get("Material Type", "").strip()
                        
                        if not jurisdiction_name or not material_name:
                            print(f"  ⚠️  Row {i}: Missing jurisdiction or material")
                            skipped += 1
                            continue
                        
                        # Get IDs from mappings
                        jurisdiction_id = jurisdictions.get(jurisdiction_name)
                        material_id = materials.get(material_name)
                        
                        if not jurisdiction_id:
                            errors.append(f"Row {i}: Jurisdiction '{jurisdiction_name}' not found")
                            skipped += 1
                            continue
                        
                        if not material_id:
                            errors.append(f"Row {i}: Material '{material_name}' not found")
                            skipped += 1
                            continue
                        
                        # Parse percentages (remove % sign and handle '-' for missing values)
                        wastage_str = row.get("Construction wastage rate (%)", "").strip().replace("%", "")
                        recycling_str = row.get("Recycling Rate (%)", "").strip().replace("%", "")
                        landfill_str = row.get("Landfill Rate (%)", "").strip().replace("%", "")
                        
                        # Handle missing values (-)
                        def parse_percent(val):
                            if val in ("", "-"):
                                return Decimal("0")
                            try:
                                return Decimal(val)
                            except (ValueError, ArithmeticError):
                                return Decimal("0")
                        
                        construction_wastage_rate = parse_percent(wastage_str)
                        recycling_rate = parse_percent(recycling_str)
                        landfill_rate = parse_percent(landfill_str)
                        source = row.get("Source/Comments", "").strip() or None
                        
                        # Check if already exists (for idempotency)
                        existing_query = await session.execute(
                            text("SELECT id FROM default_wastage_rates WHERE jurisdiction_id = :jid AND material_id = :mid AND dataset_revision_id IS NULL"),
                            {"jid": jurisdiction_id, "mid": material_id}
                        )
                        if existing_query.scalar():
                            skipped += 1
                            continue
                        
                        # Create the wastage rate record
                        payload = DefaultWastageRateCreate(
                            jurisdiction_id=jurisdiction_id,
                            material_id=material_id,
                            construction_wastage_rate=construction_wastage_rate,
                            recycling_rate=recycling_rate,
                            landfill_rate=landfill_rate,
                            source=source,
                            dataset_revision_id=None,  # Global data
                        )
                        
                        obj = await create_wastage_rate(session, payload)
                        created += 1
                        print(f"  ✓ Created wastage rate for {material_name} ({jurisdiction_name})")
                        
                    except Exception as e:
                        errors.append(f"Row {i}: {str(e)}")
                        skipped += 1
                
                # Commit all changes
                await session.commit()
            
            print(f"\n✅ Seeding complete:")
            print(f"   Created: {created}")
            print(f"   Skipped: {skipped}")
            
            if errors:
                print(f"\n⚠️  Errors encountered:")
                for error in errors[:10]:  # Show first 10 errors
                    print(f"   - {error}")
                if len(errors) > 10:
                    print(f"   ... and {len(errors) - 10} more errors")
        
        except Exception as e:
            print(f"❌ Error during seeding: {str(e)}")
            import traceback
            traceback.print_exc()
    
    await engine.dispose()


if __name__ == "__main__":
    print("🌱 Starting wastage rates seeding...")
    asyncio.run(seed_wastage_rates())

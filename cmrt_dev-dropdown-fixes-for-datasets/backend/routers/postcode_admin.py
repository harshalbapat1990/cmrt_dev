from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
import pandas as pd
import io

from core.session import get_session
from models.postcode import PostcodeReference, AreaClass
from models.jurisdictions import Jurisdiction
from crud import postcode as crud_postcode

router = APIRouter(prefix="/api/admin/postcodes", tags=["admin"])

# Mapping from CSV area class names to enum values
AREA_CLASS_MAPPING = {
    "METROPOLITAN": AreaClass.METROPOLITAN,
    "REGIONAL": AreaClass.REGIONAL,
    "REMOTE": AreaClass.REMOTE,
    "RURAL": AreaClass.RURAL,
}

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_postcode_reference(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_session)
):
    """
    Upload the Postcode reference file (Excel or CSV) with columns:
      - 'Jurisdiction' (Australia, New Zealand, etc.)
      - 'Postal code'
      - 'Final CMRT Area' (values: Metropolitan / Regional / Remote / Rural)
      - Optional: 'Remoteness area', '% inclusion', 'ALL areas' (informational)
    
    On upload, we upsert rows into postcode_reference.
    Handles batch processing for large files (5000+ rows).
    """
    fname = (file.filename or "").lower()
    is_excel = fname.endswith((".xlsx", ".xls"))
    is_csv = fname.endswith(".csv")
    
    if not (is_excel or is_csv):
        raise HTTPException(
            status_code=400, 
            detail="Only Excel (.xlsx, .xls) or CSV (.csv) files are supported"
        )

    try:
        # Read file into DataFrame
        if is_excel:
            df = pd.read_excel(file.file, engine="openpyxl")
        else:  # CSV
            content = await file.read()
            df = pd.read_csv(io.StringIO(content.decode('utf-8')))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {e}")

    # Validate required columns
    required_cols = {"Jurisdiction", "Postal code", "Final CMRT Area"}
    cols = set(df.columns)
    if not required_cols.issubset(cols):
        raise HTTPException(
            status_code=400,
            detail=f"File must contain columns: {', '.join(required_cols)}. Found: {', '.join(cols)}"
        )

    # Get all jurisdictions for mapping
    jur_result = await db.execute(select(Jurisdiction))
    jurisdictions = {jur.name: jur.id for jur in jur_result.scalars().all()}
    
    if not jurisdictions:
        raise HTTPException(
            status_code=400,
            detail="No jurisdictions found in database. Please seed jurisdictions first."
        )

    # Normalize rows
    df = df.dropna(subset=["Postal code", "Final CMRT Area"]).copy()
    df["Postal code"] = df["Postal code"].astype(str).str.strip()
    df["Final CMRT Area"] = df["Final CMRT Area"].astype(str).str.strip().str.upper()
    df["Jurisdiction"] = df["Jurisdiction"].astype(str).str.strip()

    # Process rows with batch commits (for large files)
    updated = 0
    created = 0
    errors = []
    batch_size = 500
    batch_records = []

    for idx, row in df.iterrows():
        try:
            postcode = row["Postal code"]
            area_raw = row["Final CMRT Area"]
            jurisdiction_name = row["Jurisdiction"]

            # Validate area class
            if area_raw not in AREA_CLASS_MAPPING:
                errors.append(
                    f"Row {idx + 2}: Invalid area class '{area_raw}' for postcode {postcode}. "
                    f"Allowed: METROPOLITAN / REGIONAL / REMOTE / RURAL"
                )
                continue

            # Validate jurisdiction
            if jurisdiction_name not in jurisdictions:
                errors.append(
                    f"Row {idx + 2}: Jurisdiction '{jurisdiction_name}' not found. "
                    f"Available: {', '.join(jurisdictions.keys())}"
                )
                continue

            jurisdiction_id = jurisdictions[jurisdiction_name]
            area = AREA_CLASS_MAPPING[area_raw]

            # Upsert record
            record, is_created = await crud_postcode.upsert_postcode_reference(
                db, postcode, jurisdiction_id, area
            )
            
            if is_created:
                created += 1
            else:
                updated += 1

            batch_records.append(record)

            # Commit in batches
            if len(batch_records) >= batch_size:
                await db.commit()
                batch_records = []

        except Exception as e:
            errors.append(f"Row {idx + 2}: {str(e)}")

    # Final commit for remaining records
    if batch_records:
        await db.commit()

    return {
        "status": "ok",
        "created": created,
        "updated": updated,
        "total_processed": created + updated,
        "errors": errors[:20] if errors else [],  # Return first 20 errors
        "error_count": len(errors),
    }
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
from core.session import get_session
from crud import postcode as crud_postcode
from schemas.postcode import PostcodeReference

router = APIRouter(prefix="/api/postcodes", tags=["postcode"])

@router.get("/get-all-postcodes", response_model=List[PostcodeReference])
async def get_all_postcodes(db: AsyncSession = Depends(get_session)):
    """Fetch all postcode reference records with jurisdiction data."""
    return await crud_postcode.get_all_postcode_references(db)

@router.get("/get-postcode/{postcode}/{jurisdiction_id}", response_model=PostcodeReference)
async def get_postcode_by_postcode_and_jurisdiction(
    postcode: str, jurisdiction_id: UUID, db: AsyncSession = Depends(get_session)
):
    """Fetch a postcode reference record by postcode and jurisdiction."""
    record = await crud_postcode.get_postcode_reference_by_postcode(db, postcode, jurisdiction_id)
    if not record:
        raise HTTPException(status_code=404, detail="Postcode not found for this jurisdiction")
    return record

@router.get("/get-by-jurisdiction/{jurisdiction_id}", response_model=List[PostcodeReference])
async def get_postcodes_by_jurisdiction(
    jurisdiction_id: UUID, db: AsyncSession = Depends(get_session)
):
    """Fetch all postcodes for a specific jurisdiction."""
    return await crud_postcode.get_postcode_references_by_jurisdiction(db, jurisdiction_id)

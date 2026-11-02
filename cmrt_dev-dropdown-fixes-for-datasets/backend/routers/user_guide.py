from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from core.rbac import SUPER_ADMIN, require_role
from core.security import Principal, get_current_principal
from core.session import get_session
from crud import user_guides as crud
from schemas.user_guides import UserGuideUploadResponse, UserGuideVersionOut
from services import storage_service

router = APIRouter(prefix="/api/user-guide", tags=["user-guide"])

_ALLOWED_MIME = "application/pdf"
_MAX_SIZE_BYTES = 50 * 1024 * 1024


@router.get("/", response_model=UserGuideVersionOut)
async def get_active_guide(
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    record = await crud.get_active(db)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No User Guide has been uploaded yet.",
        )
    return record


@router.get("/{guide_id}/file")
async def download_guide(
    guide_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    record = await crud.get_by_id(db, guide_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guide not found.")
    content = await storage_service.load_file(db, record)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{record.filename}"',
            "Content-Length": str(len(content)),
        },
    )


@router.get("/versions", response_model=List[UserGuideVersionOut])
async def list_versions(
    _: None = Depends(require_role(SUPER_ADMIN)),
    db: AsyncSession = Depends(get_session),
):
    return await crud.get_all_versions(db)


@router.post(
    "/upload",
    response_model=UserGuideUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_guide(
    file: UploadFile = File(...),
    _: None = Depends(require_role(SUPER_ADMIN)),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    fname = (file.filename or "").lower()
    if not fname.endswith(".pdf") or file.content_type not in (_ALLOWED_MIME, "binary/octet-stream"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files (.pdf) are accepted.",
        )

    content = await file.read()

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if len(content) > _MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {_MAX_SIZE_BYTES // (1024 * 1024)} MB limit.",
        )

    if not content.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File does not appear to be a valid PDF.",
        )

    record = await crud.create_version(
        db,
        filename=file.filename or "user-guide.pdf",
        file_size=len(content),
        uploaded_by_id=principal.user_id,
    )

    await storage_service.save_file(db, record, content)
    await db.commit()
    await db.refresh(record)
    return record


@router.put("/{guide_id}/activate", response_model=UserGuideVersionOut)
async def activate_version(
    guide_id: UUID,
    _: None = Depends(require_role(SUPER_ADMIN)),
    db: AsyncSession = Depends(get_session),
):
    record = await crud.activate_version(db, guide_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guide not found.")
    await db.commit()
    return record

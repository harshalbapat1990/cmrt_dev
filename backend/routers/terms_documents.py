from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from core.rbac import SUPER_ADMIN, require_role
from core.security import Principal, get_current_principal, get_optional_principal
from core.session import get_session
from crud import terms_documents as crud
from models.terms_documents import TermsDocumentType
from schemas.terms_documents import TermsDocumentOut, TermsDocumentUploadResponse
from services import storage_service

router = APIRouter(prefix="/api/terms-documents", tags=["terms-documents"])

_ALLOWED_MIME = "application/pdf"
_MAX_SIZE_BYTES = 50 * 1024 * 1024


@router.get("/{document_type}", response_model=TermsDocumentOut)
async def get_active_document(
    document_type: TermsDocumentType,
    # Optional: shown during registration, before the caller has a CMRT account.
    principal: Principal | None = Depends(get_optional_principal),
    db: AsyncSession = Depends(get_session),
):
    record = await crud.get_active(db, document_type)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No document has been uploaded yet.",
        )
    return record


@router.get("/{document_type}/{doc_id}/file")
async def download_document(
    document_type: TermsDocumentType,
    doc_id: UUID,
    # Optional: shown during registration, before the caller has a CMRT account.
    principal: Principal | None = Depends(get_optional_principal),
    db: AsyncSession = Depends(get_session),
):
    record = await crud.get_by_id(db, doc_id)
    if record is None or record.document_type != document_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    content = await storage_service.load_file(db, record)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{record.filename}"',
            "Content-Length": str(len(content)),
        },
    )


@router.get("/{document_type}/versions", response_model=List[TermsDocumentOut])
async def list_versions(
    document_type: TermsDocumentType,
    _: None = Depends(require_role(SUPER_ADMIN)),
    db: AsyncSession = Depends(get_session),
):
    return await crud.get_all_versions(db, document_type)


@router.post(
    "/{document_type}/upload",
    response_model=TermsDocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    document_type: TermsDocumentType,
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
        document_type=document_type,
        filename=file.filename or f"{document_type.value}.pdf",
        file_size=len(content),
        uploaded_by_id=principal.user_id,
    )

    await storage_service.save_file(db, record, content)
    await db.commit()
    await db.refresh(record)
    return record


@router.put("/{document_type}/{doc_id}/activate", response_model=TermsDocumentOut)
async def activate_version(
    document_type: TermsDocumentType,
    doc_id: UUID,
    _: None = Depends(require_role(SUPER_ADMIN)),
    db: AsyncSession = Depends(get_session),
):
    record = await crud.activate_version(db, doc_id)
    if record is None or record.document_type != document_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    await db.commit()
    return record

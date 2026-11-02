from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.terms_documents import TermsDocument, TermsDocumentType


async def get_next_version(db: AsyncSession, document_type: TermsDocumentType) -> int:
    result = await db.execute(
        select(TermsDocument.version).where(TermsDocument.document_type == document_type)
    )
    versions = result.scalars().all()
    return (max(versions) + 1) if versions else 1


async def deactivate_all(db: AsyncSession, document_type: TermsDocumentType) -> None:
    await db.execute(
        update(TermsDocument)
        .where(TermsDocument.document_type == document_type)
        .values(is_active=False)
    )


async def create_version(
    db: AsyncSession,
    *,
    document_type: TermsDocumentType,
    filename: str,
    file_size: int,
    uploaded_by_id: Optional[UUID],
) -> TermsDocument:
    version = await get_next_version(db, document_type)
    await deactivate_all(db, document_type)

    record = TermsDocument(
        document_type=document_type,
        version=version,
        filename=filename,
        file_size=file_size,
        uploaded_by_id=uploaded_by_id,
        is_active=True,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record


async def get_active(db: AsyncSession, document_type: TermsDocumentType) -> Optional[TermsDocument]:
    result = await db.execute(
        select(TermsDocument)
        .where(TermsDocument.document_type == document_type, TermsDocument.is_active == True)  # noqa: E712
        .limit(1)
    )
    return result.scalars().first()


async def get_all_versions(db: AsyncSession, document_type: TermsDocumentType) -> List[TermsDocument]:
    result = await db.execute(
        select(TermsDocument)
        .where(TermsDocument.document_type == document_type)
        .order_by(TermsDocument.version.desc())
    )
    return list(result.scalars().all())


async def get_by_id(db: AsyncSession, doc_id: UUID) -> Optional[TermsDocument]:
    result = await db.execute(select(TermsDocument).where(TermsDocument.id == doc_id))
    return result.scalars().first()


async def activate_version(db: AsyncSession, doc_id: UUID) -> Optional[TermsDocument]:
    record = await get_by_id(db, doc_id)
    if record is None:
        return None
    await deactivate_all(db, record.document_type)
    record.is_active = True
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record

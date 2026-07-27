"""Contractor document vault API — v2 endpoints for accessing contractor dossiers."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.security import get_current_user
from app.models.intelligence import ContractorDocument
from app.services.contractor_document_service import ContractorDocumentService
from app.db.base import get_async_session

router = APIRouter(prefix="/contractor-documents", tags=["contractor-documents"])
service = ContractorDocumentService()


@router.get("/categories")
async def get_document_categories():
    """Get list of document categories."""
    return {
        "categories": service.CATEGORIES
    }


@router.get("/{contractor_id}/documents")
async def get_contractor_documents(
    contractor_id: str,
    category: Optional[str] = Query(None, description="Filter by category"),
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    """Get all documents for a contractor."""
    documents = await service.get_contractor_documents(session, contractor_id, category)

    return {
        "contractor_id": contractor_id,
        "category": category,
        "count": len(documents),
        "documents": [
            {
                "id": doc.id,
                "filename": doc.filename,
                "category": doc.doc_category,
                "type": doc.doc_type,
                "size_bytes": doc.file_size,
                "uploaded_at": doc.created_at.isoformat() if doc.created_at else None,
            }
            for doc in documents
        ],
    }


@router.get("/{contractor_id}/summary")
async def get_contractor_dossier_summary(
    contractor_id: str,
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    """Get summary of contractor's document dossier."""
    return await service.get_contractor_dossier_summary(session, contractor_id)


@router.get("/{contractor_id}/document/{doc_id}")
async def get_document_details(
    contractor_id: str,
    doc_id: str,
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    """Get details of a specific document."""
    from sqlalchemy import select

    query = select(ContractorDocument).where(
        ContractorDocument.id == doc_id,
        ContractorDocument.contractor_id == contractor_id,
    )
    result = await session.execute(query)
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "id": doc.id,
        "filename": doc.filename,
        "category": doc.doc_category,
        "type": doc.doc_type,
        "size_bytes": doc.file_size,
        "mime_type": doc.mime_type,
        "uploaded_at": doc.created_at.isoformat() if doc.created_at else None,
        "extracted_data": doc.extracted_data or {},
    }

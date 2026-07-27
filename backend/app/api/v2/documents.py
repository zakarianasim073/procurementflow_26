"""Phase 2: Document Management Endpoints"""

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel, field_validator
from datetime import datetime
import json
import uuid
import os

from app.db.base import get_async_session
from app.core.security import get_current_user
from app.models.phase2 import Document
from app.core.config import settings

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentBase(BaseModel):
    """Base document schema"""
    name: str
    document_type: str  # boq, tds, notice, specification, etc.
    tender_id: str
    file_path: str
    file_size: int
    mime_type: str


class DocumentCreate(DocumentBase):
    """Create document"""
    pass


class DocumentResponse(DocumentBase):
    """Document response with metadata"""
    id: str
    created_at: datetime
    updated_at: datetime
    created_by: str
    extraction_status: str = "pending"
    extracted_data: Optional[Any] = None

    @field_validator("extracted_data", mode="before")
    @classmethod
    def _parse_extracted(cls, v):
        """extracted_data is stored as a JSON string; decode it for the client."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return v
        return v

    class Config:
        from_attributes = True


@router.get("", response_model=List[DocumentResponse])
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    tender_id: Optional[str] = Query(None),
    doc_type: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """List all documents with pagination and filtering."""
    try:
        tenant_id = current_user.get("tenant_id")
        query = select(Document).where(Document.tenant_id == tenant_id)

        if tender_id:
            query = query.where(Document.tender_id == tender_id)
        if doc_type:
            query = query.where(Document.document_type == doc_type)

        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get document by ID."""
    try:
        tenant_id = current_user.get("tenant_id")
        result = await db.execute(
            select(Document).where(and_(Document.id == document_id, Document.tenant_id == tenant_id))
        )
        document = result.scalar_one_or_none()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        return document
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    document: DocumentCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Create a new document record."""
    try:
        tenant_id = current_user.get("tenant_id")
        doc_id = str(uuid.uuid4())

        new_doc = Document(
            id=doc_id,
            name=document.name,
            document_type=document.document_type,
            tender_id=document.tender_id,
            file_path=document.file_path,
            file_size=document.file_size,
            mime_type=document.mime_type,
            extraction_status="pending",
            tenant_id=tenant_id,
            created_by=current_user["id"],
        )
        db.add(new_doc)
        await db.commit()
        await db.refresh(new_doc)
        return new_doc
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    tender_id: str = Form(...),
    doc_type: str = Form(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Upload a document file."""
    file_path = None
    try:
        from app.services.file_upload_service import FileUploadService

        tenant_id = current_user.get("tenant_id")
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Tenant ID not found")

        file_path, file_size, file_hash = await FileUploadService.upload_document(
            file, tender_id, doc_type, tenant_id
        )

        doc_id = str(uuid.uuid4())
        new_doc = Document(
            id=doc_id,
            name=file.filename or "document",
            document_type=doc_type,
            tender_id=tender_id,
            file_path=file_path,
            file_size=file_size,
            mime_type=file.content_type or "application/octet-stream",
            extraction_status="pending",
            tenant_id=tenant_id,
            created_by=current_user["id"],
        )
        db.add(new_doc)
        await db.commit()
        await db.refresh(new_doc)

        return new_doc
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        if file_path:
            FileUploadService.delete_file(file_path)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Delete a document."""
    try:
        from app.services.file_upload_service import FileUploadService

        tenant_id = current_user.get("tenant_id")
        document = await db.scalar(
            select(Document).where(
                and_(Document.id == document_id, Document.tenant_id == tenant_id)
            )
        )
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        FileUploadService.delete_file(document.file_path)
        await db.delete(document)
        await db.commit()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{document_id}/extract")
async def extract_document_data(
    document_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Extract structured data from document using AI."""
    try:
        from app.services.phase2_extraction_service import DocumentExtractionService

        tenant_id = current_user.get("tenant_id")
        result = await DocumentExtractionService.extract_from_document(
            document_id, tenant_id, db
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

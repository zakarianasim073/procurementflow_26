"""Contractor document vault service — tender dossier management and PDF extraction."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.intelligence import ContractorDocument, Contractor
from app.services.storage_service import storage_service, content_type_for

logger = logging.getLogger(__name__)


class ContractorDocumentService:
    """Manages contractor tender dossier documents."""

    # Document categories
    CATEGORIES = {
        "manpower": "Manpower",
        "equipment": "Equipment",
        "financial": "Financial Statements",
        "compliance": "Compliance Documents",
        "experience": "Experience Certificates",
        "declarations": "Declarations",
        "certificates": "Certificates",
        "other": "Other Documents",
    }

    @staticmethod
    def categorize_document(filename: str) -> str:
        """Auto-categorize document based on filename."""
        filename_lower = filename.lower()

        if "manpower" in filename_lower:
            return "manpower"
        if "equipment" in filename_lower or "eqipment" in filename_lower:
            return "equipment"
        if "turnover" in filename_lower or "payment" in filename_lower:
            return "financial"
        if "vat" in filename_lower or "license" in filename_lower or "tin" in filename_lower:
            return "compliance"
        if "experience" in filename_lower or "declaration" in filename_lower:
            return "experience"
        if "declaration" in filename_lower or "commitment" in filename_lower or "affidavit" in filename_lower:
            return "declarations"
        if "nid" in filename_lower or "signature" in filename_lower:
            return "certificates"

        return "other"

    async def upload_contractor_document(
        self,
        session: AsyncSession,
        contractor_id: str,
        file_path: Path | str,
        doc_type: Optional[str] = None,
        extracted_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[ContractorDocument]:
        """Upload and store a contractor document."""
        file_path = Path(file_path)

        if not file_path.exists():
            logger.error(f"Document file not found: {file_path}")
            return None

        try:
            # Categorize document
            doc_category = self.categorize_document(file_path.name)

            # Read file bytes
            file_bytes = file_path.read_bytes()
            file_size = len(file_bytes)

            # Store in object storage
            storage_key = storage_service.object_key(
                "uploads",
                "contractor-dossier",
                contractor_id,
                doc_category,
                file_path.name
            )
            stored_key = await storage_service.astore_file(storage_key, file_path, content_type_for(file_path.name))

            # Create document record
            doc = ContractorDocument(
                contractor_id=contractor_id,
                doc_category=doc_category,
                doc_type=doc_type or "pdf",
                filename=file_path.name,
                file_path=str(file_path),
                file_size=file_size,
                mime_type=content_type_for(file_path.name),
                extracted_data=extracted_data or {},
                storage_key=stored_key,
            )

            session.add(doc)
            await session.flush()

            logger.info(f"Uploaded contractor document: {file_path.name} for contractor {contractor_id}")
            return doc

        except Exception as e:
            logger.error(f"Error uploading contractor document {file_path.name}: {e}")
            return None

    async def get_contractor_documents(
        self,
        session: AsyncSession,
        contractor_id: str,
        category: Optional[str] = None,
    ) -> list[ContractorDocument]:
        """Retrieve contractor documents by category."""
        query = select(ContractorDocument).where(ContractorDocument.contractor_id == contractor_id)

        if category:
            query = query.where(ContractorDocument.doc_category == category)

        query = query.order_by(ContractorDocument.created_at.desc())
        result = await session.execute(query)
        return result.scalars().all()

    async def get_document_by_filename(
        self,
        session: AsyncSession,
        contractor_id: str,
        filename: str,
    ) -> Optional[ContractorDocument]:
        """Retrieve a specific document by filename."""
        query = select(ContractorDocument).where(
            ContractorDocument.contractor_id == contractor_id,
            ContractorDocument.filename == filename,
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def delete_contractor_document(
        self,
        session: AsyncSession,
        document_id: str,
    ) -> bool:
        """Delete a contractor document."""
        query = select(ContractorDocument).where(ContractorDocument.id == document_id)
        result = await session.execute(query)
        doc = result.scalar_one_or_none()

        if not doc:
            return False

        try:
            # Delete from storage if exists
            if doc.storage_key:
                storage_service.delete(doc.storage_key)

            # Delete from database
            await session.delete(doc)
            await session.flush()

            logger.info(f"Deleted contractor document: {doc.filename}")
            return True

        except Exception as e:
            logger.error(f"Error deleting contractor document {document_id}: {e}")
            return False

    async def get_contractor_dossier_summary(
        self,
        session: AsyncSession,
        contractor_id: str,
    ) -> Dict[str, Any]:
        """Get summary of contractor dossier documents."""
        documents = await self.get_contractor_documents(session, contractor_id)

        # Group by category
        by_category = {}
        for doc in documents:
            if doc.doc_category not in by_category:
                by_category[doc.doc_category] = []
            by_category[doc.doc_category].append({
                "filename": doc.filename,
                "file_size": doc.file_size,
                "uploaded_at": doc.created_at.isoformat() if doc.created_at else None,
            })

        return {
            "contractor_id": contractor_id,
            "total_documents": len(documents),
            "total_size_bytes": sum(d.file_size for d in documents),
            "by_category": by_category,
            "last_updated": max((d.created_at for d in documents), default=None).isoformat() if documents else None,
        }

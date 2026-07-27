"""Phase 2: Document Extraction Service using AI Agents"""

import json
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.phase2 import Document
from app.db.base import get_async_session
from app.core.config import settings

logger = logging.getLogger(__name__)


class DocumentExtractionService:
    """Service for extracting structured data from tender documents using AI agents."""

    @staticmethod
    def _agent_payload(result: Any) -> Dict[str, Any]:
        if isinstance(result, dict):
            return result
        payload = getattr(result, "output", None)
        if isinstance(payload, dict):
            payload = dict(payload)
            payload.setdefault("timestamp", getattr(result, "created_at", None))
            return payload
        raise TypeError("Agent returned an unsupported result type")

    @staticmethod
    async def extract_from_document(
        document_id: str,
        tenant_id: str,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """Extract data from document using AI agents."""
        try:
            result = await db.execute(
                select(Document).where(
                    (Document.id == document_id) & (Document.tenant_id == tenant_id)
                )
            )
            document = result.scalar_one_or_none()

            if not document:
                return {"status": "error", "message": "Document not found"}

            # Mark extraction as in progress
            await db.execute(
                update(Document)
                .where(
                    (Document.id == document_id) & (Document.tenant_id == tenant_id)
                )
                .values(extraction_status="processing")
            )
            await db.commit()

            # Extract based on document type
            extracted_data = await DocumentExtractionService._extract_by_type(
                document.document_type,
                document.file_path,
                document.name,
            )

            # Update document with extracted data
            await db.execute(
                update(Document)
                .where(
                    (Document.id == document_id) & (Document.tenant_id == tenant_id)
                )
                .values(
                    extracted_data=json.dumps(extracted_data),
                    extraction_status="completed",
                )
            )
            await db.commit()

            return {
                "status": "success",
                "document_id": document_id,
                "extracted_data": extracted_data,
            }

        except Exception as e:
            logger.error(f"Document extraction failed: {e}")
            try:
                await db.execute(
                    update(Document)
                    .where(
                        (Document.id == document_id) & (Document.tenant_id == tenant_id)
                    )
                    .values(extraction_status="failed")
                )
                await db.commit()
            except Exception:
                pass
            return {"status": "error", "message": str(e)}

    @staticmethod
    async def _extract_by_type(
        doc_type: str, file_path: str, filename: str
    ) -> Dict[str, Any]:
        """Extract data by document type using appropriate AI agents."""

        try:
            full_path = Path(settings.BASE_DIR) / file_path
            if not full_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            if doc_type == "boq":
                return await DocumentExtractionService._extract_boq_data(full_path, filename)
            elif doc_type == "tds":
                return await DocumentExtractionService._extract_tds_data(full_path, filename)
            elif doc_type == "notice":
                return await DocumentExtractionService._extract_notice_data(full_path, filename)
            elif doc_type == "specification":
                return await DocumentExtractionService._extract_spec_data(full_path, filename)
            else:
                return {"doc_type": doc_type, "status": "unsupported_type"}
        except Exception as e:
            logger.error(f"Extraction by type failed: {e}")
            return {"doc_type": doc_type, "status": "extraction_error", "error": str(e)}

    @staticmethod
    async def _extract_boq_data(file_path: Path, filename: str) -> Dict[str, Any]:
        """Extract BOQ (Bill of Quantities) data using BOQIntelligenceAgent."""
        try:
            # Try to use BOQ Intelligence Agent if available
            from app.agents import BOQIntelligenceAgent

            agent = BOQIntelligenceAgent()
            result = DocumentExtractionService._agent_payload(
                await agent.run(file_path=str(file_path), filename=filename)
            )

            return {
                "document_type": "boq",
                "filename": filename,
                "items": result.get("items", []),
                "total_quantity": result.get("total_quantity", 0),
                "total_value": result.get("total_value", 0),
                "status": "extracted",
                "extracted_at": result.get("timestamp"),
            }
        except Exception as e:
            logger.warning(f"BOQ extraction failed, returning scaffold: {e}")
            return {
                "document_type": "boq",
                "filename": filename,
                "items": [],
                "status": "needs_manual_review",
                "error": str(e),
            }

    @staticmethod
    async def _extract_tds_data(file_path: Path, filename: str) -> Dict[str, Any]:
        """Extract TDS (Tender Data Sheet) data using SpecIntelligenceAgent."""
        try:
            from app.agents import SpecIntelligenceAgent

            agent = SpecIntelligenceAgent()
            result = DocumentExtractionService._agent_payload(
                await agent.run(file_path=str(file_path), filename=filename)
            )

            return {
                "document_type": "tds",
                "filename": filename,
                "tender_requirements": result.get("requirements", []),
                "eligibility_criteria": result.get("eligibility", []),
                "technical_specifications": result.get("specifications", []),
                "status": "extracted",
                "extracted_at": result.get("timestamp"),
            }
        except Exception as e:
            logger.warning(f"TDS extraction failed: {e}")
            return {
                "document_type": "tds",
                "filename": filename,
                "status": "needs_manual_review",
                "error": str(e),
            }

    @staticmethod
    async def _extract_notice_data(file_path: Path, filename: str) -> Dict[str, Any]:
        """Extract Notice data using DocumentAIAgent."""
        try:
            from app.agents import DocumentAIAgent

            agent = DocumentAIAgent()
            result = DocumentExtractionService._agent_payload(
                await agent.run(file_path=str(file_path), filename=filename)
            )

            return {
                "document_type": "notice",
                "filename": filename,
                "tender_id": result.get("tender_id"),
                "agency": result.get("agency"),
                "deadline": result.get("deadline"),
                "estimated_value": result.get("estimated_value"),
                "status": "extracted",
                "extracted_at": result.get("timestamp"),
            }
        except Exception as e:
            logger.warning(f"Notice extraction failed: {e}")
            return {
                "document_type": "notice",
                "filename": filename,
                "status": "needs_manual_review",
                "error": str(e),
            }

    @staticmethod
    async def _extract_spec_data(file_path: Path, filename: str) -> Dict[str, Any]:
        """Extract Specification data using SpecIntelligenceAgent."""
        try:
            from app.agents import SpecIntelligenceAgent

            agent = SpecIntelligenceAgent()
            result = DocumentExtractionService._agent_payload(
                await agent.run(file_path=str(file_path), filename=filename)
            )

            return {
                "document_type": "specification",
                "filename": filename,
                "materials": result.get("materials", []),
                "standards": result.get("standards", []),
                "quality_requirements": result.get("quality", []),
                "status": "extracted",
                "extracted_at": result.get("timestamp"),
            }
        except Exception as e:
            logger.warning(f"Specification extraction failed: {e}")
            return {
                "document_type": "specification",
                "filename": filename,
                "status": "needs_manual_review",
                "error": str(e),
            }

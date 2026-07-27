"""Phase 2: File Upload and Storage Service"""

import os
import hashlib
import re
from pathlib import Path
from typing import Optional, Tuple
from fastapi import UploadFile

from app.core.config import settings


class FileUploadService:
    """Service for handling file uploads and storage."""

    UPLOAD_DIR = Path(settings.BASE_DIR) / "uploads" / "documents"
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    ALLOWED_TYPES = {
        "application/pdf": ".pdf",
        "application/vnd.ms-excel": ".xls",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        "application/msword": ".doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "text/plain": ".txt",
    }
    _SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9._-]+$")

    @staticmethod
    def _validate_component(value: str, field: str) -> str:
        if not value or value in {".", ".."} or not FileUploadService._SAFE_COMPONENT.fullmatch(value):
            raise ValueError(f"Invalid {field}")
        return value

    @staticmethod
    async def upload_document(
        file: UploadFile, tender_id: str, doc_type: str, tenant_id: str
    ) -> Tuple[str, int, str]:
        """Upload document and return file_path, file_size, file_hash."""
        try:
            if not file.filename:
                raise ValueError("Filename is required")

            if file.content_type and file.content_type not in FileUploadService.ALLOWED_TYPES:
                raise ValueError(f"File type {file.content_type} not allowed")

            # Create tenant/tender directory structure
            safe_tenant_id = FileUploadService._validate_component(tenant_id, "tenant_id")
            safe_tender_id = FileUploadService._validate_component(tender_id, "tender_id")
            safe_doc_type = FileUploadService._validate_component(doc_type, "doc_type")
            safe_original_name = Path(file.filename).name
            upload_root = FileUploadService.UPLOAD_DIR.resolve()
            tenant_dir = (upload_root / safe_tenant_id / safe_tender_id).resolve()
            if upload_root not in tenant_dir.parents:
                raise ValueError("Invalid upload path")
            tenant_dir.mkdir(parents=True, exist_ok=True)

            # Read file and validate size
            content = await file.read()
            file_size = len(content)

            if file_size > FileUploadService.MAX_FILE_SIZE:
                raise ValueError(f"File size {file_size} exceeds max {FileUploadService.MAX_FILE_SIZE}")

            # Generate unique filename with hash
            file_hash = hashlib.sha256(content).hexdigest()[:8]
            ext = FileUploadService.ALLOWED_TYPES.get(file.content_type, "")
            filename = f"{safe_doc_type}_{file_hash}_{safe_original_name}{ext}"

            # Save file
            file_path = (tenant_dir / filename).resolve()
            if tenant_dir not in file_path.parents:
                raise ValueError("Invalid upload path")
            with open(file_path, "wb") as f:
                f.write(content)

            # Return relative path for storage in database
            relative_path = str(file_path.relative_to(Path(settings.BASE_DIR).resolve()))

            return relative_path, file_size, file_hash

        except Exception as e:
            raise Exception(f"File upload failed: {str(e)}")

    @staticmethod
    def get_file_path(file_path: str) -> Optional[Path]:
        """Get full file path from stored path."""
        upload_root = FileUploadService.UPLOAD_DIR.resolve()
        full_path = (Path(settings.BASE_DIR).resolve() / file_path).resolve()
        if upload_root not in full_path.parents:
            return None
        if full_path.exists() and full_path.is_file():
            return full_path
        return None

    @staticmethod
    def delete_file(file_path: str) -> bool:
        """Delete a file from storage."""
        try:
            full_path = FileUploadService.get_file_path(file_path)
            if full_path:
                full_path.unlink()
                return True
            return False
        except Exception:
            return False

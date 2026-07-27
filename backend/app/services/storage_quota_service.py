"""Phase 2: Storage Quota and Cleanup Management"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.phase2 import Document
from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageQuotaService:
    """Manage storage quotas and cleanup for tenants."""

    @staticmethod
    async def get_tenant_storage_usage(tenant_id: str, db: AsyncSession) -> float:
        """Get total storage usage for a tenant in GB."""
        try:
            result = await db.execute(
                select(func.sum(Document.file_size)).where(
                    Document.tenant_id == tenant_id
                )
            )
            total_bytes = result.scalar() or 0
            return total_bytes / (1024 ** 3)  # Convert to GB
        except Exception as e:
            logger.error(f"Failed to calculate storage usage: {e}")
            return 0.0

    @staticmethod
    async def check_quota(tenant_id: str, required_bytes: int, db: AsyncSession) -> bool:
        """Check if tenant has quota for additional storage."""
        try:
            current_usage_gb = await StorageQuotaService.get_tenant_storage_usage(
                tenant_id, db
            )
            quota_gb = settings.STORAGE_QUOTA_PER_TENANT_GB
            required_gb = required_bytes / (1024 ** 3)

            if current_usage_gb + required_gb > quota_gb:
                logger.warning(
                    f"Tenant {tenant_id} quota exceeded: {current_usage_gb}GB + {required_gb}GB > {quota_gb}GB"
                )
                return False
            return True
        except Exception as e:
            logger.error(f"Quota check failed: {e}")
            return False

    @staticmethod
    async def cleanup_old_documents(days: int = None, db: AsyncSession = None) -> int:
        """Delete documents older than specified days."""
        if days is None:
            days = settings.CLEANUP_JOB_INTERVAL_DAYS

        if not settings.CLEANUP_JOB_ENABLED:
            logger.info("Cleanup job is disabled")
            return 0

        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            # Find old documents
            result = await db.execute(
                select(Document).where(Document.created_at < cutoff_date)
            )
            old_docs = result.scalars().all()

            deleted_count = 0
            for doc in old_docs:
                try:
                    # Delete file from storage
                    from app.services.file_upload_service import FileUploadService

                    FileUploadService.delete_file(doc.file_path)

                    # Delete database record
                    await db.delete(doc)
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Failed to cleanup document {doc.id}: {e}")

            if deleted_count > 0:
                await db.commit()
                logger.info(f"Cleanup job: deleted {deleted_count} old documents")

            return deleted_count

        except Exception as e:
            logger.error(f"Cleanup job failed: {e}")
            return 0

    @staticmethod
    async def get_tenant_storage_stats(tenant_id: str, db: AsyncSession) -> dict:
        """Get detailed storage statistics for a tenant."""
        try:
            # Total usage
            current_usage_gb = await StorageQuotaService.get_tenant_storage_usage(
                tenant_id, db
            )

            # Document count
            result = await db.execute(
                select(func.count(Document.id)).where(
                    Document.tenant_id == tenant_id
                )
            )
            doc_count = result.scalar() or 0

            # By type
            result = await db.execute(
                select(Document.document_type, func.sum(Document.file_size)).where(
                    Document.tenant_id == tenant_id
                ).group_by(Document.document_type)
            )
            by_type = {
                doc_type: size / (1024 ** 3) for doc_type, size in result.all()
            }

            quota_gb = settings.STORAGE_QUOTA_PER_TENANT_GB
            remaining_gb = max(0, quota_gb - current_usage_gb)

            return {
                "tenant_id": tenant_id,
                "current_usage_gb": round(current_usage_gb, 2),
                "quota_gb": quota_gb,
                "remaining_gb": round(remaining_gb, 2),
                "usage_percent": round((current_usage_gb / quota_gb * 100), 1),
                "document_count": doc_count,
                "by_type": {k: round(v, 2) for k, v in by_type.items()},
            }
        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {
                "tenant_id": tenant_id,
                "error": str(e),
            }

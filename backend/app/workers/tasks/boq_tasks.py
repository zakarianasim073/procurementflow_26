"""
Procurement Flow Specialist BD — BOQ Processing Celery Tasks
Background wrappers for BOQ comparison and export generation.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional
from pathlib import Path

from app.celery_app import celery_app
from app.services.boq_processor import BOQProcessor
from app.sor.sor_service import sor_service

logger = logging.getLogger("procureflow.tasks.boq")


# ── T-013 (API-01): async BOQ comparison job ────────────────────────────


async def _execute_compare_job(job_id: str) -> Dict[str, Any]:
    """Run a queued BOQJob through the shared compare flow and record its outcome."""
    from app.db.base import get_session_factory
    from app.db.database import apply_tenant_context, tenant_context
    from app.models.boq import BOQJob

    factory = get_session_factory()
    async with factory() as db:
        job = await db.get(BOQJob, job_id)
        if job is None:
            logger.error("BOQ job %s not found", job_id)
            return {"job_id": job_id, "status": "NOT_FOUND"}

        # Tenant context captured at submit time, applied via the central
        # mechanism (SEC-02/T-015, ADR-007/020)
        with tenant_context(job.params.get("tenant_id")):
            await apply_tenant_context(db)
            return await _run_compare_job(db, job)


async def _run_compare_job(db, job) -> Dict[str, Any]:
    from app.models.boq import BOQJobStatus
    from app.services import boq_compare_service as flow

    job_id = job.id
    job.status = BOQJobStatus.RUNNING
    job.progress = 10
    await db.commit()

    try:
        if job.kind == "compare":
            boq_path = _locate_boq_upload(job.params)
            response, comparison_id = await flow.run_compare_flow(
                db,
                boq_path=boq_path,
                boq_file_id=job.params["boq_file_id"],
                sor_agency=job.params.get("sor_agency", "BWDB"),
                zone=job.params.get("zone"),
                tender_info_dict=dict(job.params.get("tender_info") or {}),
                user_id=job.user_id,
            )
        else:  # brain_compare
            response, comparison_id = await flow.run_brain_compare_flow(
                db,
                tender_id=job.params["tender_id"],
                sor_agency=job.params.get("sor_agency", "BWDB"),
                zone=job.params.get("zone"),
                user_id=job.user_id,
            )

        job.status = BOQJobStatus.SUCCESS
        job.progress = 100
        job.comparison_id = comparison_id
        # Response-only extras; the full item payload lives on the tender row
        job.result_meta = {
            k: response.get(k)
            for k in ("financial_check", "estimated_cost_app", "tender_notice", "source")
            if k in response
        }
        await db.commit()
        logger.info("BOQ job %s completed: comparison %s", job_id, comparison_id)
        return {"job_id": job_id, "status": job.status, "comparison_id": comparison_id}
    except Exception as exc:
        await db.rollback()
        job.status = BOQJobStatus.FAILED
        job.error = str(exc)[:2000]
        await db.commit()
        logger.error("BOQ job %s failed: %s", job_id, exc)
        return {"job_id": job_id, "status": job.status, "error": job.error}


def _locate_boq_upload(params: Dict[str, Any]) -> str:
    """Find the uploaded BOQ locally; fall back to the object store (T-010)."""
    from app.core.config import settings

    boq_file_id = params["boq_file_id"]
    upload_dir = Path(settings.BASE_DIR) / "uploads"
    matches = list(upload_dir.glob(f"{boq_file_id}.*"))
    if matches:
        return str(matches[0])

    object_key = params.get("upload_object_key")
    if object_key:
        from app.services.storage_service import storage_service

        data = storage_service.fetch_bytes(object_key)
        if data:
            dest = upload_dir / Path(object_key).name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            return str(dest)

    raise FileNotFoundError(f"BOQ file {boq_file_id} not found")


@celery_app.task(bind=True)
def run_boq_compare_job(self, job_id: str) -> Dict[str, Any]:
    """Async offload for /boq/compare and /boq/brain-compare (ADR-004).

    No retries: a failed comparison must surface as a FAILED job with its
    error message, never re-run silently or hang PENDING.
    """

    async def _run() -> Dict[str, Any]:
        try:
            return await _execute_compare_job(job_id)
        finally:
            # Each task runs in its own asyncio.run() loop; the cached async
            # engine binds connections to that loop, so it must be disposed
            # before the loop closes or the next job in this worker breaks.
            from app.db.base import close_db

            await close_db()

    return asyncio.run(_run())


@celery_app.task(bind=True, max_retries=3, name="process_boq_comparison_task")
def process_boq_comparison_task(self, boq_path: str, sor_agency: str = "BWDB",
                                  zone: Optional[str] = None,
                                  tender_info: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Process BOQ comparison in the background.
    Returns the full comparison result with all items, summary, and flagged items.
    """
    if tender_info is None:
        tender_info = {}
    
    try:
        processor = BOQProcessor()
        result = asyncio.run(
            processor.compare(
                boq_path=boq_path,
                sor_agency=sor_agency,
                zone=zone,
                sor_service=sor_service,
                tender_info=tender_info,
            )
        )
        return result
    except Exception as exc:
        logger.error(f"BOQ comparison task failed: {exc}")
        self.retry(exc=exc, countdown=10)


@celery_app.task(bind=True, max_retries=2, name="generate_export_task")
def generate_export_task(self, comparison_id: str, format: str = "xlsx",
                          output_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate Excel or DOCX export from comparison results.
    """
    try:
        from app.db.base import get_session_factory
        from app.models.boq import BOQComparison
        from sqlalchemy import select
        
        # Fetch comparison from DB
        factory = get_session_factory()
        session = factory()
        try:
            stmt = select(BOQComparison).where(BOQComparison.id == comparison_id)
            comparison = session.execute(stmt).scalar_one_or_none()
            if not comparison:
                return {"error": "Comparison not found", "status": "failed"}
            
            # Generate export
            if format == "xlsx":
                from app.services.excel_export import generate_excel_export
                path = generate_excel_export(comparison, output_dir)
            else:
                from app.services.docx_export import generate_docx_export
                path = generate_docx_export(comparison, output_dir)
            
            return {"status": "success", "file_path": str(path), "format": format}
        finally:
            session.close()
    except Exception as exc:
        logger.error(f"Export generation task failed: {exc}")
        self.retry(exc=exc, countdown=10)
        
        try:
            async def _fetch_and_export():
                async with factory() as session:
                    stmt = select(BOQComparison).where(BOQComparison.id == comparison_id)
                    result = await session.execute(stmt)
                    comparison = result.scalar_one_or_none()
                    
                    if not comparison:
                        return {"error": "Comparison not found", "status": "failed"}
                    
                    if format == "xlsx" and comparison.excel_path:
                        return {
                            "status": "success",
                            "format": format,
                            "path": comparison.excel_path,
                        }
                    elif format == "docx" and comparison.docx_path:
                        return {
                            "status": "success",
                            "format": format,
                            "path": comparison.docx_path,
                        }
                    
                    return {
                        "status": "success",
                        "format": format,
                        "path": None,
                        "message": "Export file not yet generated",
                    }
            
            return loop.run_until_complete(_fetch_and_export())
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Export task failed: {exc}")
        self.retry(exc=exc, countdown=10)

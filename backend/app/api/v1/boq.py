"""BOQ API routes — thin delegates to services.boq_compare_service (T-013)."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, Dict, Any, List
import uuid
from pathlib import Path

from app.db.base import get_async_session
from app.models.intelligence import KnowledgeEntry
from app.models.boq import BOQComparison, BOQItem, BOQJob, BOQJobStatus
from app.models.tender import Tender
from app.schemas.boq import BOQComparisonCreate, BOQComparisonRead, BOQJobStatusRead
from app.core.config import settings
from app.core.security import get_optional_user, get_current_user
from app.schemas.response_models import BOQLatestResponse, BOQUploadResponse, SuccessWithData
from app.services.boq_compare_service import (
    BOQCompareError,
    build_boq_item_row,
    resolve_owner_user_id,
    run_brain_compare_flow,
    run_compare_flow,
)

router = APIRouter(prefix="/boq", tags=["boq"])

# Backward-compat alias — persistence mapping moved to boq_compare_service (T-013)
_build_boq_item_row = build_boq_item_row


async def _submit_boq_job(db: AsyncSession, *, user_id: str, kind: str, params: Dict[str, Any]) -> JSONResponse:
    """Persist a PENDING BOQJob, enqueue it on the default queue, return 202."""
    from app.workers.tasks.boq_tasks import run_boq_compare_job

    job = BOQJob(
        id=str(uuid.uuid4()),
        user_id=user_id,
        kind=kind,
        status=BOQJobStatus.PENDING,
        progress=0,
        params=params,
    )
    db.add(job)
    await db.commit()

    try:
        async_result = run_boq_compare_job.delay(job.id)
    except Exception as exc:
        job.status = BOQJobStatus.FAILED
        job.error = f"Failed to enqueue: {exc}"[:2000]
        await db.commit()
        raise HTTPException(status_code=503, detail="Comparison queue unavailable")

    job.celery_task_id = async_result.id
    await db.commit()
    return JSONResponse(
        status_code=202,
        content={"job_id": job.id, "status": job.status, "status_url": f"/api/boq/jobs/{job.id}"},
    )


async def _get_scoped_job(db: AsyncSession, job_id: str, user: Optional[dict]) -> BOQJob:
    """Tenant-scoped job lookup: non-owners get the same 404 as a missing job.

    Ownership uses the same resolution as submission (guest/demo tokens map to
    the system user), so a caller can always poll the jobs they submitted.
    """
    job = await db.get(BOQJob, job_id)
    if job is None or job.user_id != await resolve_owner_user_id(db, user):
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/compare")
async def compare_boq(
    boq_file_id: str = Form(...),
    sor_agency: str = Form("BWDB"),
    zone: Optional[str] = Form(None),
    tender_info: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_async_session),
    user: Optional[dict] = Depends(get_optional_user),
):
    """Compare BOQ against SOR rates.

    Default (ADR-004): returns 202 + job_id; the comparison runs in Celery.
    BOQ_SYNC_FALLBACK=true restores the legacy synchronous response for one
    deprecation window.
    """
    import json

    tender_info_dict = {}
    if tender_info:
        try:
            tender_info_dict = json.loads(tender_info)
        except Exception:
            pass

    upload_dir = Path(settings.BASE_DIR) / "uploads"
    boq_files = list(upload_dir.glob(f"{boq_file_id}.*"))
    if not boq_files:
        raise HTTPException(status_code=404, detail=f"BOQ file {boq_file_id} not found")

    user_id = await resolve_owner_user_id(db, user)

    if settings.BOQ_SYNC_FALLBACK:
        response, _ = await run_compare_flow(
            db,
            boq_path=str(boq_files[0]),
            boq_file_id=boq_file_id,
            sor_agency=sor_agency,
            zone=zone,
            tender_info_dict=tender_info_dict,
            user_id=user_id,
        )
        return response

    # Object key lets a worker on another replica fetch the upload (T-010)
    from app.services.storage_service import storage_service

    return await _submit_boq_job(
        db,
        user_id=user_id,
        kind="compare",
        params={
            "boq_file_id": boq_file_id,
            "sor_agency": sor_agency,
            "zone": zone,
            "tender_info": tender_info_dict,
            "tenant_id": (user or {}).get("tenant_id"),
            "upload_object_key": storage_service.object_key("uploads", boq_files[0].name),
        },
    )


@router.post("/brain-compare")
async def brain_compare_boq(
    tender_id: str = Form(...),
    sor_agency: str = Form("BWDB"),
    zone: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_async_session),
    user: Optional[dict] = Depends(get_optional_user),
):
    """Compare BOQ against SOR rates using brain knowledge entries (no file upload needed).

    Default (ADR-004): returns 202 + job_id. BOQ_SYNC_FALLBACK=true restores
    the legacy synchronous response.
    """
    # Cheap existence check so a missing tender still 404s at submit time
    doc_entry = await db.execute(
        select(KnowledgeEntry).where(
            KnowledgeEntry.entry_type == "tender_document",
            KnowledgeEntry.tender_id == tender_id,
        ).order_by(KnowledgeEntry.created_at.desc()).limit(1)
    )
    if doc_entry.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail=f"No tender_document knowledge found for tender {tender_id}")

    user_id = await resolve_owner_user_id(db, user)

    if settings.BOQ_SYNC_FALLBACK:
        try:
            response, _ = await run_brain_compare_flow(
                db,
                tender_id=tender_id,
                sor_agency=sor_agency,
                zone=zone,
                user_id=user_id,
            )
        except BOQCompareError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc))
        return response

    return await _submit_boq_job(
        db,
        user_id=user_id,
        kind="brain_compare",
        params={
            "tender_id": tender_id,
            "sor_agency": sor_agency,
            "zone": zone,
            "tenant_id": (user or {}).get("tenant_id"),
        },
    )

@router.get("/jobs/{job_id}", response_model=BOQJobStatusRead)
async def get_boq_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_async_session),
    user: Optional[dict] = Depends(get_optional_user),
):
    """Cheap indexed job-status read for polling (T-013/ADR-004)."""
    job = await _get_scoped_job(db, job_id, user)
    return BOQJobStatusRead(
        job_id=job.id,
        kind=job.kind,
        status=job.status,
        progress=job.progress,
        error=job.error,
        comparison_id=job.comparison_id,
        result_url=f"/api/boq/jobs/{job.id}/result" if job.status == BOQJobStatus.SUCCESS else None,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get("/jobs/{job_id}/result", response_model=SuccessWithData)
async def get_boq_job_result(
    job_id: str,
    db: AsyncSession = Depends(get_async_session),
    user: Optional[dict] = Depends(get_optional_user),
):
    """Full comparison payload for a completed job — same shape as the legacy sync response."""
    job = await _get_scoped_job(db, job_id, user)
    if job.status != BOQJobStatus.SUCCESS:
        raise HTTPException(
            status_code=409,
            detail={"job_id": job.id, "status": job.status, "error": job.error},
        )

    comparison = await db.get(BOQComparison, job.comparison_id) if job.comparison_id else None
    if comparison is None:
        raise HTTPException(status_code=404, detail="Comparison result not found")

    result: Dict[str, Any] = {}
    if comparison.tender_id:
        tender = await db.get(Tender, comparison.tender_id)
        if tender and tender.comparison_results:
            result = dict(tender.comparison_results)

    response = {**result, **(job.result_meta or {})}

    # Artifact links: presigned object-store URLs when available (T-010)
    from app.services.storage_service import storage_service

    if comparison.excel_object_key:
        response["excel_url"] = await storage_service.apresigned_url(comparison.excel_object_key)
    if comparison.docx_object_key:
        response["docx_url"] = await storage_service.apresigned_url(comparison.docx_object_key)
    return response


@router.post("/upload", response_model=BOQUploadResponse)
async def upload_boq(
    file: UploadFile = File(...),
    file_type: str = Form("boq"),
    user: dict = Depends(get_current_user),
):
    """Upload BOQ file (PDF, Excel, Word, or authenticated e-GP text export)."""
    # File type validation — size cap shared with the upload middleware (T-006)
    from app.core.upload_validation import MAX_FILE_SIZE
    ALLOWED_TYPES = {"pdf", "xlsx", "xls", "docx", "doc", "txt"}

    ext = Path(file.filename).suffix.lower() if file.filename else ""
    file_ext = ext.lstrip(".")

    if file_ext not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {file_ext}. Allowed: {', '.join(ALLOWED_TYPES)}"
        )

    # Size validation
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {len(content) / 1024 / 1024:.1f} MB. Max: {MAX_FILE_SIZE / 1024 / 1024:.0f} MB"
        )

    try:
        fid = str(uuid.uuid4())[:8]
        dest = Path(settings.BASE_DIR) / "uploads" / f"{fid}{ext}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            f.write(content)
        # T-010: mirror into the object store (local copy kept for downstream readers)
        from app.services.storage_service import storage_service, content_type_for
        object_key = await storage_service.astore_bytes(
            storage_service.object_key("uploads", f"{fid}{ext}"),
            content,
            content_type_for(file.filename or ""),
        )
        return {
            "success": True, "file_id": fid, "filename": file.filename,
            "file_type": file_ext, "size_bytes": len(content),
            "object_key": object_key,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/export/{file_id}")
async def export_comparison(
    file_id: str,
    format: str = Query("xlsx", pattern="^(xlsx|docx)$"),
    db: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_optional_user),
):
    """Export comparison result as Excel or DOCX"""
    # Find the comparison in database
    from sqlalchemy import select
    stmt = select(BOQComparison).where(BOQComparison.boq_file_id == file_id)
    result = await db.execute(stmt)
    comparison = result.scalar_one_or_none()
    
    if not comparison:
        raise HTTPException(status_code=404, detail="Comparison not found")
    
    file_path = comparison.excel_path if format == "xlsx" else comparison.docx_path
    object_key = comparison.excel_object_key if format == "xlsx" else comparison.docx_object_key
    if not file_path or not Path(file_path).exists():
        # T-010: worker-written artifacts live in the object store, not on this
        # replica's disk — serve via presigned URL when a key is recorded.
        if object_key:
            from fastapi.responses import RedirectResponse
            from app.services.storage_service import storage_service
            url = await storage_service.apresigned_url(object_key)
            if url:
                return RedirectResponse(url, status_code=307)
        raise HTTPException(status_code=404, detail=f"{format.upper()} file not found")

    return FileResponse(
        file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if format == "xlsx" 
                   else "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=Path(file_path).name
    )


@router.get("/latest", response_model=BOQLatestResponse)
async def get_latest_comparison(
    db: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_optional_user),
):
    """Return the latest saved comparison with BOQ item rows for dashboard/results recovery."""
    stmt = select(BOQComparison).order_by(BOQComparison.created_at.desc())
    if user and user.get("id") and user.get("id") != "guest":
        stmt = stmt.where(BOQComparison.user_id == user["id"])
    result = await db.execute(stmt.limit(1))
    comparison = result.scalar_one_or_none()
    if comparison is None:
        raise HTTPException(status_code=404, detail="No saved comparison found")

    item_rows: List[BOQItem] = []
    if comparison.tender_id:
        items_result = await db.execute(
            select(BOQItem)
            .where(BOQItem.tender_id == comparison.tender_id)
            .order_by(BOQItem.created_at.asc())
        )
        item_rows = list(items_result.scalars().all())

    # Get financial check and APP estimate from related tender
    financial_check = []
    estimated_cost_app = None
    if comparison.tender_id:
        tender_result = await db.execute(
            select(Tender).where(Tender.id == comparison.tender_id)
        )
        tender = tender_result.scalar_one_or_none()
        if tender and tender.extracted_data:
            financial_check = tender.extracted_data.get("financial_check", [])
            estimated_cost_app = tender.extracted_data.get("estimated_cost_app")

    return {
        "success": True,
        "comparison_id": comparison.id,
        "boq_file_id": comparison.boq_file_id,
        "sor_agency": comparison.sor_agency,
        "zone": comparison.zone,
        "items": [
            {
                "item_no": item.item_no or "",
                "code": item.code or "",
                "agency": item.agency or comparison.sor_agency,
                "work_type": item.work_type or "",
                "desc": item.description or "",
                "unit": item.unit or "",
                "qty": item.quantity,
                "rate": item.quoted_rate,
                "sor_rate": item.sor_rate,
                "sor_source": item.sor_code,
                "diff": item.diff,
                "pct_diff": item.pct_diff,
                "flag": item.flag or "",
                "section": item.section or "",
            }
            for item in item_rows
        ],
        "summary": {
            "by_work_type": comparison.summary_by_work_type or [],
            "total_sor": comparison.total_sor_amount or 0.0,
            "total_quoted": comparison.total_quoted_amount or 0.0,
            "discount_pct": comparison.discount_pct or 0.0,
        },
        "flagged": [],
        "total_items": comparison.total_items,
        "mismatches": comparison.mismatches,
        "variances": comparison.variances,
        "matches": comparison.matches,
        "below_sor": comparison.below_sor,
        "excel_path": comparison.excel_path,
        "docx_path": comparison.docx_path,
        "tenderai_dir": comparison.tenderai_dir,
        "created_at": comparison.created_at.isoformat(),
        "financial_check": financial_check,
        "estimated_cost_app": estimated_cost_app,
    }


@router.get("/history", response_model=List[BOQComparisonRead])
async def get_comparison_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    """Get user's BOQ comparison history"""
    from sqlalchemy import select, desc
    stmt = select(BOQComparison).where(BOQComparison.user_id == user["id"]).order_by(desc(BOQComparison.created_at)).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{comparison_id}", response_model=BOQComparisonRead)
async def get_comparison(
    comparison_id: str,
    db: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    """Get specific comparison details"""
    from sqlalchemy import select
    stmt = select(BOQComparison).where(BOQComparison.id == comparison_id, BOQComparison.user_id == user["id"])
    result = await db.execute(stmt)
    comparison = result.scalar_one_or_none()
    if not comparison:
        raise HTTPException(status_code=404, detail="Comparison not found")
    return comparison

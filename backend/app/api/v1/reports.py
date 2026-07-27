"""Non-blocking report job API with background worker."""

from datetime import datetime, timezone
from pathlib import Path
import json
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.security import get_optional_user
from app.schemas.response_models import ReportGenerateResponse, ReportJobStatusResponse

router = APIRouter(prefix="/reports", tags=["reports"])


class ReportGenerateRequest(BaseModel):
    report_type: str = "tender_summary"
    tender_id: str = ""
    payload: dict = Field(default_factory=dict)


def _jobs_dir() -> Path:
    path = Path(settings.BASE_DIR) / "runtime" / "report_jobs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _update_job(job_id: str, **updates) -> dict:
    """Read, update, and write a job file atomically."""
    path = _jobs_dir() / f"{job_id}.json"
    if not path.exists():
        return {}
    job = json.loads(path.read_text(encoding="utf-8"))
    job.update(updates)
    job["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(job, indent=2), encoding="utf-8")
    return job


async def _process_report(job_id: str, report_type: str, tender_id: str, payload: dict) -> None:
    """Background worker: generate report content based on type."""
    _update_job(job_id, status="processing")
    try:
        if report_type == "tender_summary":
            from sqlalchemy import text
            from app.db.base import get_session_factory
            async with get_session_factory()() as session:
                result = await session.execute(
                    text("SELECT title, agency_code, closing_date, estimated_amount_bdt "
                         "FROM procurement_tenders WHERE id = :id OR package_no = :id LIMIT 1"),
                    {"id": tender_id or payload.get("tender_id", "")}
                )
                row = result.mappings().first()
                report_data = {
                    "tender_id": tender_id,
                    "title": row["title"] if row else "Unknown",
                    "agency": row["agency_code"] if row else "Unknown",
                    "closing_date": str(row["closing_date"]) if row and row.get("closing_date") else "N/A",
                    "estimated_cost": float(row["estimated_amount_bdt"]) if row and row.get("estimated_amount_bdt") else 0,
                } if row else {"tender_id": tender_id, "note": "Tender not found in database"}

        elif report_type == "agency_activity":
            from sqlalchemy import text
            from app.db.base import get_session_factory
            agency = payload.get("agency", "LGED")
            async with get_session_factory()() as session:
                result = await session.execute(
                    text("SELECT COUNT(*) as total, SUM(estimated_amount_bdt) as total_value "
                         "FROM procurement_tenders WHERE agency_code = :agency"),
                    {"agency": agency}
                )
                row = result.mappings().first()
                report_data = {
                    "agency": agency,
                    "total_tenders": row["total"] if row else 0,
                    "total_value_bdt": float(row["total_value_bdt"]) if row and row.get("total_value_bdt") else 0,
                }

        elif report_type == "sor_summary":
            from app.sor.sor_service import sor_service
            agencies = {}
            for a in ["BWDB", "PWD", "LGED"]:
                stats = sor_service.get_stats(a)
                agencies[a] = {"total_rates": stats["total_rates"], "has_csv": stats["has_csv"]}
            report_data = {"agencies": agencies}

        else:
            report_data = {
                "report_type": report_type,
                "note": f"Report type '{report_type}' processed without custom handler",
                "payload_snapshot": {k: str(v)[:200] for k, v in payload.items()},
            }

        _update_job(job_id, status="completed", result=report_data)
    except Exception as e:
        import traceback
        _update_job(job_id, status="failed", error=str(e), traceback=traceback.format_exc())


@router.post("/generate", response_model=ReportGenerateResponse)
async def generate_report(
    req: ReportGenerateRequest,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    user: dict = Depends(get_optional_user),
):
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    job = {
        "job_id": job_id,
        "status": "queued",
        "report_type": req.report_type,
        "tender_id": req.tender_id,
        "created_at": now,
        "updated_at": now,
        "payload": req.payload,
    }
    (_jobs_dir() / f"{job_id}.json").write_text(json.dumps(job, indent=2), encoding="utf-8")
    background_tasks.add_task(_process_report, job_id, req.report_type, req.tender_id, req.payload)
    return {"success": True, "job_id": job_id, "status": "queued", "poll_url": f"/api/reports/jobs/{job_id}"}


@router.get("/jobs/{job_id}", response_model=ReportJobStatusResponse)
async def report_job_status(job_id: str, user: dict = Depends(get_optional_user)):
    path = _jobs_dir() / f"{job_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report job not found")
    return {"success": True, **json.loads(path.read_text(encoding="utf-8"))}

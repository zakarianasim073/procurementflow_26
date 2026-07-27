"""Crawl orchestration endpoints (T-024: CrawlImportService)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.celery_app import celery_app
from app.db.base import get_async_session
from app.schemas.response_models import CrawlerListResponse, CrawlStartResponse, CrawlStatusResponse
from app.services.crawl_import_service import CrawlImportService

router = APIRouter(prefix="/crawl", tags=["crawl"])

@router.post("/start", response_model=CrawlStartResponse)
async def start_crawl(
    crawl_type: str = "all",
    max_pages: int = 50,
) -> Dict[str, Any]:
    """Start a crawl by type: app, tender, award, experience, debarment, documents, or 'all'."""
    allowed_types = {"all", "app", "tender", "award", "documents", "experience", "debarment"}
    if crawl_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Unknown crawl type: {crawl_type}")
    from app.workers.tasks.crawl_tasks import run_crawl_import_task

    task = run_crawl_import_task.delay(crawl_type, max_pages)
    return {"run_id": task.id, "status": "started", "type": crawl_type}


@router.get("/status/{run_id}", response_model=CrawlStatusResponse)
async def get_crawl_status(run_id: str, db: AsyncSession = Depends(get_async_session)) -> Dict[str, Any]:
    """Get status of a crawl job."""
    task = celery_app.AsyncResult(run_id)
    status = task.state.lower()
    stats = task.result if task.successful() and isinstance(task.result, dict) else {}
    return {"run_id": run_id, "status": status, "type": stats.get("type", ""), "stats": stats}


@router.get("/crawlers", response_model=CrawlerListResponse)
async def list_crawlers(db: AsyncSession = Depends(get_async_session)) -> Dict[str, Any]:
    """List available crawlers."""
    service = CrawlImportService(db)
    return {"crawlers": service.get_available_crawlers()}

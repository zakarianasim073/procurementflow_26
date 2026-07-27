"""Crawler orchestration API — ProcureFlow integration layer.

Exposes the crawler framework (backend/crawler/) to the main FastAPI app so
the frontend and other agents can trigger crawls and poll their status without
shell access.

Key design decisions:
- /run returns immediately with a task_id (never blocks for minutes).
- /jobs/{task_id} lets callers poll status from the TaskQueue.
- /run-all enqueues every plugin and returns a list of task_ids.
- Orchestrator is a lazily-initialised singleton; the shutdown handler tears it down.
- Both Python-registered plugins (registry.py) and YAML-declared plugins (loader.py)
  are discovered on every plugin-listing call.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from backend.crawler.framework.config import settings as crawler_settings
from backend.crawler.framework.logger import get_logger
from backend.crawler.plugins.loader import discover_yaml_configs
from backend.crawler.plugins.registry import (
    discover_plugins,
    discover_plugins_from_yaml,
    get as get_plugin_cls,
    get_manifest,
    list_manifests,
    list_plugins,
)
from backend.crawler.utils.app_listings import ALL_FYS
from backend.crawler.workers.orchestrator import CrawlerOrchestrator
from backend.crawler.workers.task_queue import TaskPriority, TaskStatus

log = get_logger("crawler.api")
router = APIRouter(prefix="/crawler", tags=["crawler"])

_orchestrator: Optional[CrawlerOrchestrator] = None
_orchestrator_lock = asyncio.Lock()


def _discover_all():
    """Discover both Python-registered and YAML-declared plugins."""
    discover_plugins()
    discover_plugins_from_yaml()


async def get_orchestrator() -> CrawlerOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        async with _orchestrator_lock:
            if _orchestrator is None:
                o = CrawlerOrchestrator()
                await o.start()
                _orchestrator = o
    return _orchestrator


@router.on_event("shutdown")
async def shutdown_orchestrator():
    global _orchestrator
    if _orchestrator is not None:
        await _orchestrator.stop()
        _orchestrator = None


# ── Plugin discovery ──────────────────────────────────────────────────────────

@router.get("/plugins")
async def list_crawler_plugins():
    """List all available crawler plugins (Python-registered + YAML-declared)."""
    _discover_all()
    manifests = list_manifests()
    plugins = {
        p: {"type": "python", "version": "1.0.0", "manifest": manifests.get(p, {})}
        for p in list_plugins()
    }
    return {"plugins": plugins, "count": len(plugins)}


@router.get("/plugins/{plugin_name}")
async def get_plugin_manifest(plugin_name: str):
    _discover_all()
    manifest = get_manifest(plugin_name)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_name}' not found")
    return {"plugin": plugin_name, "manifest": manifest.to_dict()}


# ── Run (async — returns task_id immediately) ─────────────────────────────────

@router.post("/run")
async def run_plugin(
    plugin: str = Query(..., description="Plugin name"),
    mode: str = Query("incremental", pattern="^(incremental|full|verify|resume)$"),
    max_pages: Optional[int] = Query(None, ge=1),
    page_size: Optional[int] = Query(None, ge=1, le=200),
    search_mode: Optional[str] = Query(None, pattern="^(details|listings)$"),
    view_types: Optional[str] = Query(None, description="Comma-separated e.g. Live,Archive"),
    timeout: Optional[float] = Query(None, ge=10, le=300),
    tender_ids: Optional[str] = Query(None, description="Comma-separated tender IDs (documents plugin)"),
    from_brain: Optional[bool] = Query(None, description="Fetch pending tender IDs from tender listings"),
    priority: str = Query("default", pattern="^(high|default|low)$"),
):
    """
    Enqueue a single plugin and return a task_id immediately.

    Poll ``GET /crawler/jobs/{task_id}`` for status and results.
    """
    _discover_all()
    if not get_plugin_cls(plugin):
        yaml_dir = crawler_settings.output_dir.parent.parent / "config"
        yaml_plugins = discover_yaml_configs(yaml_dir)
        if plugin not in yaml_plugins:
            raise HTTPException(status_code=404, detail=f"Plugin '{plugin}' not found")

    config: Dict[str, Any] = {"mode": mode}
    if max_pages:
        config["max_pages"] = max_pages
    if page_size:
        config["page_size"] = page_size
    if search_mode:
        config["search_mode"] = search_mode
    if view_types:
        config["view_types"] = [v.strip() for v in view_types.split(",")]
    if timeout:
        config["timeout"] = timeout
    if tender_ids:
        config["tender_ids"] = [t.strip() for t in tender_ids.split(",")]
    if from_brain is not None:
        config["from_brain"] = from_brain

    prio = {"high": TaskPriority.HIGH, "default": TaskPriority.DEFAULT, "low": TaskPriority.LOW}[priority]

    orch = await get_orchestrator()
    task_id = await orch.run_plugin_async(plugin, config=config, priority=prio)
    return {
        "task_id": task_id,
        "plugin": plugin,
        "status": "queued",
        "poll": f"/api/v1/crawler/jobs/{task_id}",
    }


@router.get("/jobs/{task_id}")
async def get_job_status(task_id: str):
    """Poll the status of an enqueued crawler task."""
    orch = _orchestrator
    if orch is None:
        raise HTTPException(status_code=503, detail="Orchestrator not started")
    task = orch.get_task_status(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

    result = None
    if task["status"] == TaskStatus.COMPLETED.value:
        raw = orch.task_queue.get_result(task_id)
        if raw and raw.result:
            r = raw.result
            result = {
                "status": r.status,
                "pages_done": r.pages_done,
                "items_done": r.items_done,
                "items_skipped": r.items_skipped,
                "items_failed": r.items_failed,
                "error": r.error,
            }
    return {
        "task_id": task_id,
        "name": task["name"],
        "status": task["status"],
        "error": task.get("error"),
        "result": result,
    }


@router.get("/jobs")
async def list_jobs():
    """List all enqueued/running/completed jobs from the current session."""
    orch = _orchestrator
    if orch is None:
        return {"jobs": [], "total": 0}
    queue = orch.task_queue
    if queue is None:
        return {"jobs": [], "total": 0}
    jobs = []
    for task_id, task in queue._results.items():
        jobs.append({
            "task_id": task_id,
            "name": task.name,
            "status": task.status.value,
            "error": task.error,
        })
    return {"jobs": jobs, "total": len(jobs)}


# ── Run-all (parallel, returns list of task_ids) ──────────────────────────────

@router.post("/run-all")
async def run_all_plugins(
    mode: str = Query("incremental", pattern="^(incremental|full|verify|resume)$"),
    max_pages: Optional[int] = Query(None, ge=1),
    plugins: Optional[str] = Query(None, description="Comma-separated subset; omit for all"),
):
    """
    Enqueue every plugin concurrently and return their task_ids.

    Poll each ``GET /crawler/jobs/{task_id}`` individually to track progress.
    """
    _discover_all()
    target = [p.strip() for p in plugins.split(",")] if plugins else list_plugins()
    config: Dict[str, Any] = {"mode": mode}
    if max_pages:
        config["max_pages"] = max_pages

    orch = await get_orchestrator()
    task_ids = {}
    for name in target:
        task_id = await orch.run_plugin_async(name, config=config)
        task_ids[name] = task_id

    return {
        "queued": len(task_ids),
        "tasks": [
            {"plugin": name, "task_id": tid, "poll": f"/api/v1/crawler/jobs/{tid}"}
            for name, tid in task_ids.items()
        ],
    }


# ── Status / health ───────────────────────────────────────────────────────────

@router.get("/status")
async def crawler_status():
    """Orchestrator health — is it running and what subsystems are up?"""
    orch = _orchestrator
    if orch is None:
        return {"running": False, "orchestrator": None}
    q = orch.task_queue
    return {
        "running": orch.is_running,
        "browser": orch.browser is not None,
        "session": orch.session is not None,
        "downloader": orch.downloader is not None,
        "queue": {
            "pending": q.pending_count if q else 0,
            "max_concurrent": q._max_concurrent if q else 0,
        },
    }


# ── APP listings (SearchServlet, no Playwright) ───────────────────────────────

@router.post("/listings")
async def crawl_app_listings(
    start_fy: Optional[str] = Query(None, description="Start FY e.g. 2025-2026"),
    max_pages: Optional[int] = Query(None, ge=1, le=100),
    fys: Optional[str] = Query(None, description="Comma-separated FYs (overrides start_fy)"),
):
    """Crawl Annual Procurement Plan listings via SearchServlet (no browser required)."""
    target_fys = [f.strip() for f in fys.split(",")] if fys else None
    if target_fys:
        invalid = [f for f in target_fys if f not in ALL_FYS]
        if invalid:
            raise HTTPException(status_code=400, detail=f"Invalid FYs: {invalid}")
    from backend.crawler.utils.app_listings import crawl_all_fys
    output_dir = crawler_settings.output_dir / "APP_BY_FY"
    results = await asyncio.to_thread(
        crawl_all_fys,
        output_dir=output_dir,
        start_fy=start_fy,
        max_pages=max_pages,
    )
    return {
        "total_records": sum(results.values()),
        "fys_crawled": len(results),
        "details": results,
    }


@router.post("/test-searchservlet")
async def test_searchservlet(
    fy: str = Query("2025-2026", description="Financial Year"),
    pages: int = Query(1, ge=1, le=5),
):
    """Quick smoke-test: fetch a small sample of APP listing pages and return them."""
    from pathlib import Path
    import tempfile
    import httpx
    from backend.crawler.utils.app_listings import crawl_fy_listings, ALL_FYS, discover_total_pages

    if fy not in ALL_FYS:
        raise HTTPException(status_code=400, detail=f"Invalid FY. Choose from: {', '.join(ALL_FYS)}")

    def _run_test():
        client = httpx.Client(follow_redirects=True, timeout=70)
        tmp = None
        try:
            client.get("https://www.eprocure.gov.bd")
            total = discover_total_pages(client, fy)
            tmp = Path(tempfile.mkdtemp())
            records = crawl_fy_listings(fy, client, tmp, tmp / "_ck.json", max_pages=pages)
            sample = records[:3] if records else []
            for item in sample:
                if "estimated_cost_bdt" in item:
                    item["estimated_cost_bdt"] = float(item["estimated_cost_bdt"]) if item["estimated_cost_bdt"] else None
            return {
                "financial_year": fy,
                "total_pages_on_server": total,
                "pages_fetched": pages,
                "records_fetched": len(records),
                "sample": sample,
            }
        finally:
            client.close()
            if tmp is not None:
                import shutil
                shutil.rmtree(tmp, ignore_errors=True)

    return await asyncio.to_thread(_run_test)

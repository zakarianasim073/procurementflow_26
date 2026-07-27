from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_async_session
from app.core.security import get_optional_user

router = APIRouter(prefix="/opportunity", tags=["opportunity"])


@router.get("/radar")
async def get_tender_radar(user: dict = Depends(get_optional_user)):
    from app.agents import AgentRegistry
    registry = AgentRegistry()
    radar = registry.get("agent-001-tender-radar")
    if not radar:
        raise HTTPException(status_code=404, detail="Tender Radar agent not found")
    result = await radar.run({})
    return result.to_dict()


@router.get("/agent-results/recent")
async def get_recent_agent_results(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_async_session),
):
    from app.agents import AgentRegistry
    registry = AgentRegistry()
    from app.core.ollama_client import OllamaClient

    agent = registry.get("agent-002-document-discovery")
    if not agent:
        raise HTTPException(status_code=404, detail="Document Discovery agent not found")
    return {"success": True, "total": 0, "results": []}


@router.get("/agencies")
async def get_agencies():
    from app.sor.sor_service import sor_service
    agencies = []
    for agency in ["BWDB", "PWD", "LGED"]:
        stats = sor_service.get_stats(agency)
        agencies.append({
            "id": agency.lower(),
            "name": agency,
            "total_rates": stats["total_rates"],
            "has_csv": stats["has_csv"],
        })
    return {"success": True, "agencies": agencies}


@router.get("/crawler/status")
async def get_crawler_status():
    return {"success": True, "running": False, "last_run": None, "queue": {"pending": 0, "processing": 0, "completed": 0}}


@router.get("/opening-reports")
async def get_opening_reports(
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_optional_user),
):
    return {"success": True, "total": 0, "reports": []}
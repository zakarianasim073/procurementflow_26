"""Phase 1 API Routers for Contractor Intelligence Platform.

Routes:
  /api/v1/contractors/profile/{contractor_id} - Full contractor profile
  /api/v1/contractors/leaderboard/{dimension} - Leaderboards
  /api/v1/agencies/performance/{agency_code} - Agency intelligence
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from app.core.security import get_current_user
from app.db.base import get_async_session

LEADERBOARD_VIEWS = {
    "execution_score": "leaderboard_execution_score",
    "volume": "leaderboard_volume",
    "project_value": "leaderboard_project_value",
    "reliability": "leaderboard_reliability",
    "financial_scale": "leaderboard_financial_scale",
}

AGENCY_ORDER_FIELDS = {
    "total_value_bdt",
    "total_projects",
    "unique_contractors",
    "completion_rate_pct",
    "on_time_rate_pct",
    "avg_project_value_bdt",
}


router = APIRouter(tags=["contractor-intelligence"])


# ── Models ────────────────────────────────────────────────────────────

class ContractorProfile(BaseModel):
    contractor_id: str
    contractor_name: str
    total_projects: int
    completed_projects: int
    ongoing_projects: int
    total_contract_value_bdt: float
    completion_rate_pct: float
    on_time_rate_pct: float
    avg_delay_days: float
    largest_project_bdt: float
    execution_score: float
    reliability_score: float
    annual_turnover_bdt: float
    financial_exposure_bdt: float
    avg_project_value_bdt: float
    max_project_value_bdt: float
    available_capacity_score: float
    current_workload_bdt: float

class LeaderboardEntry(BaseModel):
    rank: int
    contractor_id: str
    contractor_name: str
    execution_score: float
    total_projects: int
    total_contract_value_bdt: float

class AgencyPerformance(BaseModel):
    agency_code: str
    unique_contractors: int
    total_projects: int
    completed_projects: int
    ongoing_projects: int
    avg_delay_days: float
    avg_project_value_bdt: float
    largest_project_value_bdt: float
    total_value_bdt: float
    delayed_projects_pct: float
    on_time_rate_pct: float
    completion_rate_pct: float


# ── Contractor Profile ───────────────────────────────────────────────

@router.get("/contractors/profile/{contractor_id}", response_model=ContractorProfile)
async def get_contractor_profile(
    contractor_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get complete contractor intelligence profile. Authenticated users only."""
    if not user or not user.get("tenant_id"):
        raise HTTPException(status_code=403, detail="Authentication required")
    result = await db.execute(text("""
        SELECT contractor_id, contractor_name, total_projects, completed_projects, ongoing_projects,
               total_contract_value_bdt, completion_rate_pct, on_time_rate_pct, avg_delay_days,
               largest_project_bdt, execution_score, reliability_score,
               annual_turnover_bdt, financial_exposure_bdt, avg_project_value_bdt,
               max_project_value_bdt, available_capacity_score, current_workload_bdt
        FROM contractor_profile_complete
        WHERE contractor_id = :contractor_id
    """), {"contractor_id": contractor_id})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Contractor not found")
    return dict(row)


@router.get("/contractors/profile/by-name/{contractor_name}")
async def get_contractor_by_name(
    contractor_name: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get contractor by name. Authenticated users only."""
    if not user or not user.get("tenant_id"):
        raise HTTPException(status_code=403, detail="Authentication required")
    """Search contractor by name (partial match)."""
    result = await db.execute(text("""
        SELECT contractor_id, contractor_name, execution_score, total_projects,
               total_contract_value_bdt, completion_rate_pct
        FROM contractor_profile_complete
        WHERE contractor_name ILIKE :name
        ORDER BY execution_score DESC, total_contract_value_bdt DESC
        LIMIT 20
    """), {"name": f"%{contractor_name}%"})
    rows = [dict(r) for r in result.mappings().all()]
    return {"count": len(rows), "results": rows}


# ── Leaderboards ────────────────────────────────────────────────────

@router.get("/leaderboards/{dimension}")
async def get_leaderboard(
    dimension: str,  # execution_score, volume, project_value, reliability, financial_scale
    limit: int = Query(50, ge=1, le=500),
    agency: Optional[str] = Query(None, description="Filter by agency code"),
    db: AsyncSession = Depends(get_async_session),
):
    """Get ranked contractor leaderboard by dimension.
    
    Dimensions:
    - execution_score: Best execution track record
    - volume: Most projects completed
    - project_value: Largest single project value
    - reliability: Best on-time delivery rate
    - financial_scale: Highest annual turnover
    """
    view = LEADERBOARD_VIEWS.get(dimension)
    if not view:
        raise HTTPException(status_code=400, detail=f"Invalid dimension. Use: {', '.join(LEADERBOARD_VIEWS.keys())}")
    
    if agency:
        # Filter by agency using contractor_profile_by_agency
        result = await db.execute(text("""
            SELECT cpc.contractor_id, cpc.contractor_name, cpc.execution_score,
                   cpc.total_projects, cpc.total_contract_value_bdt,
                   cae.agency_code, cae.total_projects as agency_projects,
                   cae.total_value_bdt as agency_value
            FROM contractor_profile_complete cpc
            JOIN contractor_agency_experience cae ON cpc.contractor_name = cae.contractor_name
            WHERE cae.agency_code = :agency
            ORDER BY cpc.execution_score DESC, cpc.total_contract_value_bdt DESC
            LIMIT :limit
        """), {"agency": agency, "limit": limit})
    else:
        # sql-ok: view from LEADERBOARD_VIEWS allowlist
        result = await db.execute(text(f"SELECT * FROM {view} LIMIT :limit"), {"limit": limit})
    
    rows = [dict(r) for r in result.mappings().all()]
    return {"dimension": dimension, "agency_filter": agency, "count": len(rows), "results": rows}


@router.get("/leaderboards/agency/{agency_code}")
async def get_agency_leaderboard(
    agency_code: str,
    dimension: str = Query("execution_score"),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_async_session),
):
    """Get top contractors for a specific agency."""
    result = await db.execute(text("""
        SELECT cpc.contractor_id, cpc.contractor_name, cae.total_projects as projects_with_agency,
               cae.completed_projects as completed_with_agency,
               cae.total_value_bdt as value_with_agency,
               cae.on_time_rate as agency_on_time_rate,
               cpc.execution_score, cpc.total_projects as total_projects_all,
               cpc.total_contract_value_bdt as total_value_all
        FROM contractor_profile_complete cpc
        JOIN contractor_agency_experience cae ON cpc.contractor_name = cae.contractor_name
        WHERE cae.agency_code = :agency_code
        ORDER BY cae.total_value_bdt DESC, cpc.execution_score DESC
        LIMIT :limit
    """), {"agency_code": agency_code, "limit": limit})
    
    rows = [dict(r) for r in result.mappings().all()]
    return {"agency": agency_code, "dimension": dimension, "count": len(rows), "results": rows}


# ── Agency Intelligence ──────────────────────────────────────────────

@router.get("/agencies/performance/{agency_code}", response_model=AgencyPerformance)
async def get_agency_performance(
    agency_code: str,
    db: AsyncSession = Depends(get_async_session),
):
    """Get performance intelligence for a specific agency."""
    result = await db.execute(text("""
        SELECT * FROM agency_performance_summary WHERE agency_code = :agency_code
    """), {"agency_code": agency_code})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Agency not found")
    return dict(row)


@router.get("/agencies/performance")
async def list_agency_performance(
    limit: int = Query(50, ge=1, le=500),
    order_by: str = Query("total_value_bdt", description="Sort field: total_value_bdt, total_projects, unique_contractors, completion_rate_pct"),
    db: AsyncSession = Depends(get_async_session),
):
    """List all agencies with performance summary."""
    if order_by not in AGENCY_ORDER_FIELDS:
        order_by = "total_value_bdt"
    
    # sql-ok: order_by validated against AGENCY_ORDER_FIELDS allowlist
    result = await db.execute(text(f"""
        SELECT * FROM agency_performance_summary
        ORDER BY {order_by} DESC
        LIMIT :limit
    """), {"limit": limit})
    
    rows = [dict(r) for r in result.mappings().all()]
    return {"count": len(rows), "order_by": order_by, "results": rows}


@router.get("/agencies/contractors/{agency_code}")
async def get_agency_contractors(
    agency_code: str,
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_async_session),
):
    """Get all contractors who have worked with an agency, ranked by experience."""
    result = await db.execute(text("""
        SELECT cpc.contractor_id, cpc.contractor_name, cae.total_projects,
               cae.completed_projects, cae.ongoing_projects, cae.total_value_bdt,
               cae.avg_contract_value, cae.on_time_rate, cpc.execution_score
        FROM contractor_profile_complete cpc
        JOIN contractor_agency_experience cae ON cpc.contractor_name = cae.contractor_name
        WHERE cae.agency_code = :agency_code
        ORDER BY cae.total_value_bdt DESC, cpc.execution_score DESC
        LIMIT :limit
    """), {"agency_code": agency_code, "limit": limit})
    
    rows = [dict(r) for r in result.mappings().all()]
    return {"agency": agency_code, "count": len(rows), "results": rows}


# ── Dashboard Summary ─────────────────────────────────────────────────

@router.get("/dashboard/summary")
async def get_dashboard_summary(db: AsyncSession = Depends(get_async_session)):
    """Get overall platform intelligence summary."""
    # Total counts
    contractor_result = await db.execute(text("""
        SELECT 
            COUNT(*) as total_contractors,
            COUNT(*) FILTER (WHERE execution_score > 80) as excellent_contractors,
            COUNT(*) FILTER (WHERE execution_score > 60) as good_contractors,
            COUNT(*) FILTER (WHERE completion_rate_pct > 0.9) as high_completion_rate,
            COUNT(*) FILTER (WHERE on_time_rate_pct > 0.9) as high_on_time_rate,
            SUM(total_contract_value_bdt) as total_contract_value_bdt,
            SUM(total_projects) as total_projects,
            AVG(execution_score) as avg_execution_score,
            AVG(avg_delay_days) as avg_delay_days_overall
        FROM contractor_profile_complete
    """))
    contractor_summary = dict(contractor_result.mappings().one())
    
    # Agency summary
    agency_result = await db.execute(text("""
        SELECT 
            COUNT(*) as total_agencies,
            SUM(unique_contractors) as total_contractor_agency_pairs,
            SUM(total_projects) as total_agency_projects,
            SUM(total_value_bdt) as total_agency_value_bdt
        FROM agency_performance_summary
    """))
    agency_summary = dict(agency_result.mappings().one())
    
    # Work type distribution
    work_type_result = await db.execute(text("""
        SELECT work_type, SUM(total_projects) as total_projects, SUM(total_value_bdt) as total_value_bdt
        FROM contractor_work_similarity
        GROUP BY work_type
        ORDER BY total_projects DESC
    """))
    work_types = [dict(r) for r in work_type_result.mappings().all()]
    
    return {
        "contractors": contractor_summary,
        "agencies": agency_summary,
        "work_types": work_types,
        "timestamp": "now"
    }

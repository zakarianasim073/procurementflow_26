"""Phase 3: Capacity & Risk Intelligence API.

Routes:
  /api/v1/contractors/{id}/capacity       - Capacity analysis for tender
  /api/v1/contractors/{id}/financial-risk - Financial risk scoring
  /api/v1/market/leaderboards/{type}     - Domain-specific leaderboards
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_async_session

router = APIRouter(tags=["capacity-risk"])


# ── Models ────────────────────────────────────────────────────────────

class CapacityAnalysis(BaseModel):
    contractor_id: str
    contractor_name: str
    current_workload_bdt: float
    current_project_count: int
    available_financial_capacity: float
    resource_saturation_pct: float
    capacity_score: float = Field(..., ge=0, le=100)
    recommendation: str = Field(..., description="CAN_BID | RISKY_BID | OVERLEVERAGED")
    can_bid: bool
    explanation: str

class FinancialRiskScore(BaseModel):
    contractor_id: str
    contractor_name: str
    risk_level: str = Field(..., description="LOW | MEDIUM | HIGH | CRITICAL")
    risk_score: float = Field(..., ge=0, le=100)
    leverage_ratio: float
    leverage_score: float
    project_variance_cv: float
    variance_score: float
    delayed_projects_pct: float
    delay_score: float
    recommendation: str = Field(..., description="SAFE | MONITOR | RISKY")

class MarketLeaderboardEntry(BaseModel):
    rank: int
    contractor_id: str
    contractor_name: str
    metric_value: float
    supporting_value: float
    execution_score: float


# ── 3.1 Contractor Capacity Analysis ─────────────────────────────────

@router.get("/capacity-risk/{contractor_id}")
async def analyze_capacity_v2(
    contractor_id: str,
    tender_value: float = Query(0, description="Estimated tender value in BDT"),
    db: AsyncSession = Depends(get_async_session)
):
    """Analyze contractor's capacity to take on a new tender (Phase 3).
    
    Returns capacity score (0-100) and recommendation:
    - CAN_BID: Plenty of capacity, financially healthy
    - RISKY_BID: Near capacity limit or moderate leverage
    - OVERLEVERAGED: Cannot afford or fully booked
    """
    result = await db.execute(text("""
        SELECT c.contractor_name, cc.concurrent_projects, cc.current_workload_bdt,
               cc.total_award_value_bdt, cc.available_capacity_score,
               cf.annual_turnover_estimate_bdt, cf.financial_exposure_bdt
        FROM contractors c
        LEFT JOIN contractor_capacity cc ON c.contractor_name = cc.contractor_name
        LEFT JOIN contractor_finance cf ON c.contractor_name = cf.contractor_name
        WHERE c.id = :contractor_id
    """), {"contractor_id": contractor_id})
    
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Contractor not found")
    
    concurrent = row['concurrent_projects'] or 0
    workload = row['current_workload_bdt'] or 0
    total_award = row['total_award_value_bdt'] or 1
    available = row['available_capacity_score'] or 50
    annual = row['annual_turnover_estimate_bdt'] or 1
    exposure = row['financial_exposure_bdt'] or 0
    
    # Resource saturation (max 8 concurrent projects)
    resource_sat = min(concurrent / 8 * 100, 100)
    resource_score = max(0, 100 - resource_sat)
    
    # Financial capacity
    leverage = (exposure + tender_value) / max(annual, 1)
    if leverage > 2.0:
        financial_score = 20
    elif leverage > 1.5:
        financial_score = 40
    elif leverage > 1.0:
        financial_score = 60
    else:
        financial_score = 100
    
    avail_score = available if available else 50
    
    capacity_score = resource_score * 0.4 + financial_score * 0.3 + avail_score * 0.3
    
    if capacity_score >= 80:
        recommendation = "CAN_BID"
        can_bid = True
    elif capacity_score >= 50:
        recommendation = "RISKY_BID"
        can_bid = True
    else:
        recommendation = "OVERLEVERAGED"
        can_bid = False
    
    return CapacityAnalysis(
        contractor_id=contractor_id,
        contractor_name=row['contractor_name'],
        current_workload_bdt=round(workload, 0),
        current_project_count=concurrent,
        available_financial_capacity=round(max(annual * 2 - exposure, 0), 0),
        resource_saturation_pct=round(resource_sat, 1),
        capacity_score=round(capacity_score, 1),
        recommendation=recommendation,
        can_bid=can_bid,
        explanation=f"Resource saturation: {resource_sat:.0f}%. Financial leverage: {leverage:.2f}x. Available capacity: {avail_score:.0f}/100."
    )


# ── 3.2 Financial Risk Scoring ───────────────────────────────────────

@router.get("/contractors/{contractor_id}/financial-risk")
async def score_financial_risk(contractor_id: str, db: AsyncSession = Depends(get_async_session)):
    """Score contractor financial risk.
    
    Factors:
    - Leverage ratio (exposure / turnover)
    - Project volume variance (coefficient of variation)
    - Delayed projects (cash flow risk)
    
    Returns: risk_level (LOW/MEDIUM/HIGH/CRITICAL), risk_score (0-100)
    """
    result = await db.execute(text("""
        SELECT c.contractor_name, cf.annual_turnover_estimate_bdt, cf.financial_exposure_bdt,
               cf.total_award_value_bdt, cf.project_value_std_dev
        FROM contractors c
        LEFT JOIN contractor_finance cf ON c.contractor_name = cf.contractor_name
        WHERE c.id = :contractor_id
    """), {"contractor_id": contractor_id})
    
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Contractor not found")
    
    annual = row['annual_turnover_estimate_bdt'] or 1
    exposure = row['financial_exposure_bdt'] or 0
    std_dev = row['project_value_std_dev'] or 0
    
    # Leverage ratio
    leverage = exposure / max(annual, 1)
    if leverage > 2.5:
        lev_score = 20
    elif leverage > 2.0:
        lev_score = 40
    elif leverage > 1.0:
        lev_score = 60
    else:
        lev_score = 80
    
    # Project variance (CV)
    avg_val = row['total_award_value_bdt'] or 1
    cv = std_dev / max(avg_val / 10, 1)
    if cv > 1.5:
        variance_score = 40
    elif cv > 1.0:
        variance_score = 60
    else:
        variance_score = 80
    
    # Delayed projects from execution history
    d_result = await db.execute(text("""
        SELECT COUNT(*) as total,
               COUNT(*) FILTER (WHERE delay_days > 30) as delayed
        FROM contractor_execution_history
        WHERE contractor_name = :name
    """), {"name": row['contractor_name']})
    delay_row = d_result.mappings().first()
    total_exec = delay_row['total'] or 0
    delayed = delay_row['delayed'] or 0
    delay_pct = (delayed / total_exec * 100) if total_exec > 0 else 0
    
    if delay_pct > 50:
        delay_score = 20
    elif delay_pct > 25:
        delay_score = 40
    elif delay_pct > 10:
        delay_score = 60
    else:
        delay_score = 80
    
    # Composite risk score (higher = safer, inverse of risk)
    risk_score = lev_score * 0.4 + variance_score * 0.3 + delay_score * 0.3
    
    if risk_score >= 70:
        risk_level = "LOW"
        recommendation = "SAFE"
    elif risk_score >= 50:
        risk_level = "MEDIUM"
        recommendation = "MONITOR"
    elif risk_score >= 30:
        risk_level = "HIGH"
        recommendation = "RISKY"
    else:
        risk_level = "CRITICAL"
        recommendation = "RISKY"
    
    return FinancialRiskScore(
        contractor_id=contractor_id,
        contractor_name=row['contractor_name'],
        risk_level=risk_level,
        risk_score=round(risk_score, 1),
        leverage_ratio=round(leverage, 2),
        leverage_score=lev_score,
        project_variance_cv=round(cv, 2),
        variance_score=variance_score,
        delayed_projects_pct=round(delay_pct, 1),
        delay_score=delay_score,
        recommendation=recommendation
    )


# ── 3.3 Market Intelligence Leaderboards ──────────────────────────────

@router.get("/market/leaderboards/{type}")
async def market_leaderboard(
    type: str,
    filter_by: Optional[str] = Query(None, description="Filter value (e.g., agency_code, district, work_type)"),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_async_session)
):
    """Domain-specific contractor leaderboards."""
    params = {"lim": limit}
    filter_val = filter_by

    if type == "agency_top":
        agency = filter_val or "LGED"
        params["agency"] = agency
        result = await db.execute(text("""
            SELECT c.id as contractor_id, c.contractor_name,
                   cae.total_projects as metric_value, cae.total_value_bdt as supporting_value,
                   COALESCE(cd.execution_score, 0) as execution_score
            FROM contractor_agency_experience cae
            JOIN contractors c ON c.contractor_name = cae.contractor_name
            LEFT JOIN contractor_dna cd ON c.id = cd.contractor_id
            WHERE cae.agency_code = :agency
            ORDER BY cae.total_value_bdt DESC LIMIT :lim"""), params)
    elif type == "district_top":
        district = filter_val or "Dhaka"
        params["district"] = district
        result = await db.execute(text("""
            SELECT c.id as contractor_id, c.contractor_name,
                   cde.total_projects as metric_value, cde.total_value_bdt as supporting_value,
                   COALESCE(cd.execution_score, 0) as execution_score
            FROM contractor_district_experience cde
            JOIN contractors c ON c.contractor_name = cde.contractor_name
            LEFT JOIN contractor_dna cd ON c.id = cd.contractor_id
            WHERE cde.district = :district
            ORDER BY cde.total_value_bdt DESC LIMIT :lim"""), params)
    elif type == "work_type_top":
        work_type = filter_val or "Road & Highway"
        params["work_type"] = work_type
        result = await db.execute(text("""
            SELECT c.id as contractor_id, c.contractor_name,
                   cws.total_projects as metric_value, cws.total_value_bdt as supporting_value,
                   COALESCE(cd.execution_score, 0) as execution_score
            FROM contractor_work_similarity cws
            JOIN contractors c ON c.contractor_name = cws.contractor_name
            LEFT JOIN contractor_dna cd ON c.id = cd.contractor_id
            WHERE cws.work_type = :work_type
            ORDER BY cws.total_value_bdt DESC LIMIT :lim"""), params)
    elif type == "reliable":
        result = await db.execute(text("""
            SELECT c.id as contractor_id, c.contractor_name,
                   cd.on_time_rate * 100 as metric_value, cd.total_contracts as supporting_value,
                   cd.execution_score
            FROM contractor_dna cd JOIN contractors c ON c.id = cd.contractor_id
            WHERE cd.on_time_rate > 0 AND cd.total_contracts >= 5
            ORDER BY cd.on_time_rate DESC, cd.avg_delay_days ASC LIMIT :lim"""), {"lim": limit})
    elif type == "delayed":
        result = await db.execute(text("""
            SELECT c.id as contractor_id, c.contractor_name, ceh.delayed as metric_value,
                   ceh.total as supporting_value, COALESCE(cd.execution_score, 0) as execution_score
            FROM (SELECT contractor_name, COUNT(*) as total,
                         COUNT(*) FILTER (WHERE delay_days > 30) as delayed
                  FROM contractor_execution_history GROUP BY contractor_name) ceh
            JOIN contractors c ON c.contractor_name = ceh.contractor_name
            LEFT JOIN contractor_dna cd ON c.id = cd.contractor_id
            WHERE ceh.delayed > 0 ORDER BY ceh.delayed DESC LIMIT :lim"""), {"lim": limit})
    elif type == "large_projects":
        result = await db.execute(text("""
            SELECT c.id as contractor_id, c.contractor_name,
                   cd.avg_award_bdt as metric_value, cd.total_contracts as supporting_value,
                   cd.execution_score
            FROM contractor_dna cd JOIN contractors c ON c.id = cd.contractor_id
            WHERE cd.avg_award_bdt > 0 AND cd.total_contracts >= 3
            ORDER BY cd.avg_award_bdt DESC LIMIT :lim"""), {"lim": limit})
    elif type == "high_value":
        result = await db.execute(text("""
            SELECT c.id as contractor_id, c.contractor_name,
                   cd.total_amount_bdt as metric_value, cd.total_contracts as supporting_value,
                   cd.execution_score
            FROM contractor_dna cd JOIN contractors c ON c.id = cd.contractor_id
            WHERE cd.total_amount_bdt > 0 ORDER BY cd.total_amount_bdt DESC LIMIT :lim"""), {"lim": limit})
    else:
        raise HTTPException(status_code=400, detail=f"Invalid type: {type}")
    
    rows = [dict(r) for r in result.mappings().all()]
    results = []
    for i, row in enumerate(rows):
        results.append({
            "rank": i + 1,
            "contractor_id": row['contractor_id'],
            "contractor_name": row['contractor_name'],
            "metric_value": round(row['metric_value'], 1) if row['metric_value'] else 0,
            "supporting_value": round(row['supporting_value'], 0) if row['supporting_value'] else 0,
            "execution_score": round(row['execution_score'], 1) if row['execution_score'] else 0
        })
    
    return {
        "type": type,
        "filter": filter_by,
        "count": len(results),
        "results": results
    }


@router.get("/market/summary")
async def market_summary(db: AsyncSession = Depends(get_async_session)):
    """Get market intelligence summary across all dimensions."""
    # Top agencies by value
    result = await db.execute(text("""
        SELECT agency_code, COUNT(DISTINCT contractor_name) as contractors,
               SUM(total_value_bdt) as total_value, SUM(total_projects) as total_projects
        FROM contractor_agency_experience
        GROUP BY agency_code
        ORDER BY total_value DESC
        LIMIT 10
    """))
    top_agencies = [dict(r) for r in result.mappings().all()]
    
    # Top work types by value
    result = await db.execute(text("""
        SELECT work_type, SUM(total_projects) as total_projects, SUM(total_value_bdt) as total_value
        FROM contractor_work_similarity
        GROUP BY work_type
        ORDER BY total_value DESC
        LIMIT 10
    """))
    top_work_types = [dict(r) for r in result.mappings().all()]
    
    # Top districts by value
    result = await db.execute(text("""
        SELECT district, COUNT(DISTINCT contractor_name) as contractors,
               SUM(total_value_bdt) as total_value, SUM(total_projects) as total_projects
        FROM contractor_district_experience
        GROUP BY district
        ORDER BY total_value DESC
        LIMIT 10
    """))
    top_districts = [dict(r) for r in result.mappings().all()]
    
    # Market concentration stats
    result = await db.execute(text("""
        SELECT COUNT(DISTINCT agency_code) as total_agencies,
               COUNT(DISTINCT contractor_name) as total_contractors,
               SUM(total_value_bdt) as total_market_value
        FROM contractor_agency_experience
    """))
    market_stats = dict(result.mappings().first())
    
    return {
        "market_stats": market_stats,
        "top_agencies": top_agencies,
        "top_work_types": top_work_types,
        "top_districts": top_districts
    }

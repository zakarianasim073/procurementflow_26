"""Advanced analytics routes — PostgreSQL-backed."""

from typing import Optional, List, Dict, Any
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from app.db.base import get_async_session
from app.core.security import get_optional_user
from app.services.intelligence_data_service_facade import IntelligenceDataServiceFacade as IntelligenceDataService
from app.models.boq import BOQComparison

from app.schemas.response_models import SuccessResponse, SimpleSuccessResponse, SuccessWithData

router = APIRouter(prefix="/analytics", tags=["analytics"])


# ── Response Models ────────────────────────────────────────────────────
class AnalyticsOverviewResponse(BaseModel):
    """Response model for analytics overview endpoint."""
    total_tenders: int
    total_awards: int
    total_agencies: int
    total_competitors: int
    execution: Dict[str, Any]
    timestamp: str


class NppTrendsResponse(BaseModel):
    """Response model for NPP trends endpoint."""
    success: bool = True
    data: Dict[str, Any]


class AwardTrendsResponse(BaseModel):
    """Response model for award trends endpoint."""
    success: bool = True
    data: Dict[str, Any]


class AgencyComparisonResponse(BaseModel):
    """Response model for agency comparison endpoint."""
    success: bool = True
    data: Dict[str, Any]


class ContractorLeaderboardResponse(BaseModel):
    """Response model for contractor leaderboard endpoint."""
    success: bool = True
    data: Dict[str, Any]


class WinRateResponse(BaseModel):
    """Response model for win rate endpoint."""
    success: bool = True
    data: Dict[str, Any]


class DiscountDistributionResponse(BaseModel):
    """Response model for discount distribution endpoint."""
    success: bool = True
    data: Dict[str, Any]


class MonthlyTrendsResponse(BaseModel):
    """Response model for monthly trends endpoint."""
    success: bool = True
    data: Dict[str, Any]


class BOQAnalyticsResponse(BaseModel):
    """Response model for BOQ analytics endpoint."""
    success: bool = True
    data: Dict[str, Any]


class ExecutionOverviewResponse(BaseModel):
    """Response model for execution overview endpoint."""
    success: bool = True
    data: Dict[str, Any]


class ExecutionTimelineResponse(BaseModel):
    """Response model for execution timeline endpoint."""
    success: bool = True
    data: Dict[str, Any]


class ExecutionAgenciesResponse(BaseModel):
    """Response model for execution agencies endpoint."""
    success: bool = True
    data: Dict[str, Any]


class ExecutionContractorResponse(BaseModel):
    """Response model for execution contractor endpoint."""
    success: bool = True
    data: Dict[str, Any]


class ExecutionRateQuotedResponse(BaseModel):
    """Response model for execution rate quoted endpoint."""
    success: bool = True
    data: Dict[str, Any]


class AgencyComparisonDetail(BaseModel):
    """Detail model for agency comparison data."""
    agency: Optional[str] = None
    award_count: int = 0
    total_value: float = 0.0
    total_estimate: float = 0.0
    avg_discount_pct: float = 0.0
    unique_contractors: int = 0
    avg_project_size: float = 0.0


class ContractorLeaderboardItem(BaseModel):
    """Item model for contractor leaderboard."""
    name: Optional[str] = None
    total_awards: int = 0
    total_amount: float = 0.0
    avg_discount_pct: float = 0.0
    avg_project_size: float = 0.0
    agencies: List[Any] = []


class WinRateAgency(BaseModel):
    """Agency model for win rate data."""
    agency: Optional[str] = None
    total_awards: int = 0
    top_contractors: List[Dict[str, Any]] = []
    concentration_pct: float = 0.0

def get_svc(db: AsyncSession = Depends(get_async_session)) -> IntelligenceDataService:
    return IntelligenceDataService(db)


@router.get("/overview", response_model=AnalyticsOverviewResponse)
async def analytics_overview(
    svc: IntelligenceDataService = Depends(get_svc),
    user: dict = Depends(get_optional_user),
):
    lifecycle = await svc.get_lifecycle_stats()
    contractors = await svc.get_contractor_stats()
    agency_intel = await svc.get_agency_intelligence()
    ee_stats = await svc.get_eexperience_stats(source="EEXPERIENCE_ALL")
    ecms_stats = await svc.get_eexperience_stats(source="ECMS_ONGOING")
    return {
        "total_tenders": lifecycle["total_records"],
        "total_awards": lifecycle["matched_packages"],
        "total_agencies": len(agency_intel),
        "total_competitors": contractors["total_contractors"],
        "execution": {
            "completed_works": ee_stats["total_records"],
            "completed_works_value_bdt": ee_stats["total_value_bdt"],
            "completed_works_agencies": ee_stats["unique_agencies"],
            "completed_works_contractors": ee_stats["unique_contractors"],
            "ongoing_packages": ecms_stats["total_records"],
            "ongoing_packages_value_bdt": ecms_stats["total_value_bdt"],
            "ongoing_packages_agencies": ecms_stats["unique_agencies"],
            "ongoing_packages_contractors": ecms_stats["unique_contractors"],
            "delayed_records": ee_stats["delayed_records"],
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/npp-trends", response_model=NppTrendsResponse)
async def npp_trends(
    months: int = Query(12, ge=1, le=60),
    svc: IntelligenceDataService = Depends(get_svc),
    user: dict = Depends(get_optional_user),
):
    trends = await svc.get_npp_trends(months=months)
    agencies = sorted({row["agency_code"] for row in trends if row.get("agency_code")})
    return {"success": True, "data": {"trends": trends, "agencies": agencies}}


@router.get("/award-trends", response_model=AwardTrendsResponse)
async def award_trends(
    months: int = Query(12, ge=1, le=60),
    svc: IntelligenceDataService = Depends(get_svc),
    user: dict = Depends(get_optional_user),
):
    lifecycle = await svc.query_lifecycle(limit=5000)
    by_month = defaultdict(lambda: {"count": 0, "total_value": 0.0, "total_estimate": 0.0})
    for row in lifecycle["records"]:
        month = (row.get("award_date") or "")[:7]
        if not month:
            continue
        by_month[month]["count"] += 1
        by_month[month]["total_value"] += row.get("award_amount_bdt", 0) or 0
        by_month[month]["total_estimate"] += row.get("estimated_cost_bdt", 0) or 0
    series = [{"month": month, **vals} for month, vals in sorted(by_month.items())]
    return {"success": True, "data": {"award_trends": series[-months:] if months else series}}


@router.get("/agency-comparison", response_model=AgencyComparisonResponse)
async def agency_comparison(
    svc: IntelligenceDataService = Depends(get_svc),
    user: dict = Depends(get_optional_user),
):
    agencies = await svc.get_agency_intelligence()
    return {
        "success": True,
        "data": {
            "agencies": [
                {
                    "agency": row.get("agency_code"),
                    "award_count": row.get("total_contracts", 0),
                    "total_value": round(row.get("total_amount_bdt", 0) or 0, 2),
                    "total_estimate": 0,
                    "avg_discount_pct": round(max(0.0, (1 - (row.get("avg_npp", 0) or 0)) * 100), 2),
                    "unique_contractors": 0,
                    "avg_project_size": round(
                        (row.get("total_amount_bdt", 0) or 0) / max(row.get("total_contracts", 1), 1),
                        2,
                    ),
                }
                for row in agencies
            ]
        },
    }


@router.get("/agency-comparison", response_model=AgencyComparisonResponse)
async def agency_comparison(
    svc: IntelligenceDataService = Depends(get_svc),
    user: dict = Depends(get_optional_user),
):
    agencies = await svc.get_agency_intelligence()
    return {
        "success": True,
        "data": {
            "agencies": [
                {
                    "agency": row.get("agency_code"),
                    "award_count": row.get("total_contracts", 0),
                    "total_value": round(row.get("total_amount_bdt", 0) or 0, 2),
                    "total_estimate": 0,
                    "avg_discount_pct": round(max(0.0, (1 - (row.get("avg_npp", 0) or 0)) * 100), 2),
                    "unique_contractors": 0,
                    "avg_project_size": round(
                        (row.get("total_amount_bdt", 0) or 0) / max(row.get("total_contracts", 1), 1),
                        2,
                    ),
                }
                for row in agencies
            ]
        },
    }


@router.get("/contractor-leaderboard", response_model=ContractorLeaderboardResponse)
async def contractor_leaderboard(
    limit: int = Query(10, ge=1, le=100),
    sort_by: str = Query("total_awards", pattern="^(total_awards|total_amount|avg_discount|avg_project_size)$"),
    svc: IntelligenceDataService = Depends(get_svc),
    user: dict = Depends(get_optional_user),
):
    contractors = await svc.list_contractors(limit=1000, offset=0)
    leaderboard = []
    for row in contractors:
        awards = row.get("total_contracts", 0) or 0
        amount = row.get("total_amount_bdt", 0) or 0
        avg_discount = max(0.0, (1 - (row.get("avg_npp", 0) or 0)) * 100) if row.get("avg_npp") else 0.0
        leaderboard.append(
            {
                "name": row.get("contractor_name", ""),
                "total_awards": awards,
                "total_amount": amount,
                "avg_discount_pct": round(avg_discount, 2),
                "avg_project_size": round(amount / max(awards, 1), 2),
                "agencies": row.get("agencies_worked") or [],
            }
        )
    sort_map = {
        "total_awards": "total_awards",
        "total_amount": "total_amount",
        "avg_discount": "avg_discount_pct",
        "avg_project_size": "avg_project_size",
    }
    leaderboard.sort(key=lambda item: item[sort_map[sort_by]], reverse=True)
    return {"success": True, "data": {"leaderboard": leaderboard[:limit], "total_profiles": len(leaderboard)}}


@router.get("/win-rate", response_model=WinRateResponse)
async def win_rate(
    svc: IntelligenceDataService = Depends(get_svc),
    user: dict = Depends(get_optional_user),
):
    lifecycle = await svc.query_lifecycle(limit=5000)
    agency_contractor = defaultdict(lambda: defaultdict(int))
    for row in lifecycle["records"]:
        agency = row.get("agency_code") or "Unknown"
        winner = row.get("winner") or "Unknown"
        if winner and row.get("award_amount_bdt", 0):
            agency_contractor[agency][winner] += 1
    result = []
    for agency, contractor_map in sorted(agency_contractor.items()):
        total = sum(contractor_map.values())
        top = sorted(contractor_map.items(), key=lambda item: item[1], reverse=True)
        concentration = round((top[0][1] / total) * 100, 1) if total and top else 0
        result.append(
            {
                "agency": agency,
                "total_awards": total,
                "top_contractors": [
                    {"name": name, "wins": wins, "share_pct": round(wins / total * 100, 1)}
                    for name, wins in top[:5]
                ],
                "concentration_pct": concentration,
            }
        )
    return {"success": True, "data": {"agencies": result}}


@router.get("/discount-distribution", response_model=DiscountDistributionResponse)
async def discount_distribution(
    svc: IntelligenceDataService = Depends(get_svc),
    user: dict = Depends(get_optional_user),
):
    patterns = await svc.get_discount_patterns()
    distribution = []
    total_weight = 0
    avg_discount_total = 0.0
    for row in patterns:
        avg_discount = max(0.0, (1 - (row.get("avg_npp", 0) or 0)) * 100)
        bucket_start = int(avg_discount // 5) * 5
        distribution.append({"range": f"{bucket_start}-{bucket_start + 5}", "count": row.get("sample_size", 0)})
        total_weight += row.get("sample_size", 0) or 0
        avg_discount_total += avg_discount * (row.get("sample_size", 0) or 0)
    return {
        "success": True,
        "data": {
            "distribution": distribution,
            "buckets": [item["range"] for item in distribution],
            "avg_discount": round(avg_discount_total / total_weight, 2) if total_weight else 0,
            "sample_size": total_weight,
        },
    }


@router.get("/monthly-trends", response_model=MonthlyTrendsResponse)
async def monthly_trends(
    months: int = Query(12, ge=1, le=60),
    svc: IntelligenceDataService = Depends(get_svc),
    user: dict = Depends(get_optional_user),
):
    lifecycle = await svc.query_lifecycle(limit=5000)
    by_month = defaultdict(lambda: {"awards": 0, "award_value": 0.0, "predictions": 0, "evaluations": 0})
    for row in lifecycle["records"]:
        month = (row.get("award_date") or "")[:7]
        if not month:
            continue
        by_month[month]["awards"] += 1
        by_month[month]["award_value"] += row.get("award_amount_bdt", 0) or 0
    series = [{"month": month, **vals} for month, vals in sorted(by_month.items())]
    return {"success": True, "data": {"monthly_trends": series[-months:] if months else series}}


@router.get("/boq-analytics", response_model=BOQAnalyticsResponse)
async def boq_analytics(
    db: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_optional_user),
):
    stmt = select(
        func.count(BOQComparison.id).label("total_comparisons"),
        func.sum(BOQComparison.total_items).label("total_items"),
        func.sum(BOQComparison.matches).label("total_matches"),
        func.sum(BOQComparison.variances).label("total_variances"),
        func.sum(BOQComparison.mismatches).label("total_mismatches"),
        func.avg(BOQComparison.discount_pct).label("avg_discount_pct"),
    )
    res = await db.execute(stmt)
    row = res.first()
    
    if row and row.total_comparisons > 0:
        return {
            "success": True,
            "data": {
                "total_comparisons": row.total_comparisons,
                "total_items": int(row.total_items or 0),
                "total_matches": int(row.total_matches or 0),
                "total_variances": int(row.total_variances or 0),
                "total_mismatches": int(row.total_mismatches or 0),
                "avg_discount_pct": round((row.avg_discount_pct or 0.0) * 100, 2),
            },
        }
        
    return {
        "success": True,
        "data": {
            "total_comparisons": 0,
            "total_items": 0,
            "total_matches": 0,
            "total_variances": 0,
            "total_mismatches": 0,
            "avg_discount_pct": 0.0,
        },
    }


# ── Execution Analytics (eExperience / eCMS) ─────────────────────────

@router.get("/execution/overview", summary="Execution overview stats", response_model=ExecutionOverviewResponse)
async def execution_overview(
    source: Optional[str] = Query(None, description="EEXPERIENCE_ALL | ECMS_ONGOING"),
    svc: IntelligenceDataService = Depends(get_svc),
    user: dict = Depends(get_optional_user),
):
    stats = await svc.get_eexperience_stats(source=source)
    return {"success": True, "data": stats}


@router.get("/execution/timeline", summary="Execution timeline", response_model=ExecutionTimelineResponse)
async def execution_timeline(
    source: Optional[str] = Query(None),
    granularity: str = Query("month", pattern="^(month|year)$"),
    year: Optional[int] = Query(None),
    svc: IntelligenceDataService = Depends(get_svc),
    user: dict = Depends(get_optional_user),
):
    data = await svc.get_eexperience_timeline(source=source, granularity=granularity, year=year)
    return {"success": True, "data": data}


@router.get("/execution/agencies", summary="Agency execution comparison", response_model=ExecutionAgenciesResponse)
async def execution_agencies(
    source: Optional[str] = Query(None),
    svc: IntelligenceDataService = Depends(get_svc),
    user: dict = Depends(get_optional_user),
):
    data = await svc.get_agency_comparison(source=source)
    return {"success": True, "data": data}


@router.get("/execution/contractor/{name}", summary="Contractor execution performance", response_model=ExecutionContractorResponse)
async def execution_contractor(
    name: str,
    source: Optional[str] = Query(None),
    svc: IntelligenceDataService = Depends(get_svc),
    user: dict = Depends(get_optional_user),
):
    data = await svc.get_contractor_performance(contractor_name=name, source=source)
    return {"success": True, "data": data}


@router.get("/execution/rate-quoted", summary="Rate Quoted analysis — award vs completed value", response_model=ExecutionRateQuotedResponse)
async def execution_rate_quoted(
    agency: Optional[str] = Query(None),
    contractor: Optional[str] = Query(None),
    source: Optional[str] = Query(None, description="EEXPERIENCE_ALL | ECMS_ONGOING"),
    limit: int = Query(100, le=5000),
    offset: int = Query(0),
    svc: IntelligenceDataService = Depends(get_svc),
    user: dict = Depends(get_optional_user),
):
    data = await svc.get_rate_quoted_analysis(
        agency=agency, contractor=contractor, source=source, limit=limit, offset=offset,
    )
    return {"success": True, "data": data}

"""Analytics API endpoints (T-021: Intelligence Dashboard)."""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.security import get_current_user
from app.db.base import get_async_session
from app.services.analytics_warehouse import AnalyticsWarehouseService
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["analytics"])


# ── Response Models ──────────────────────────────────────────────────


class MarketOverviewResponse(BaseModel):
    """Overall market metrics."""

    total_tenders: int
    total_value_bdt: float
    avg_value_bdt: float
    awarded_count: int


class AgencyMetrics(BaseModel):
    """Agency-level market metrics."""

    agency_id: str
    agency_code: str
    agency_name: str
    tender_count: int
    total_value_bdt: float
    avg_value_bdt: float
    avg_duration_days: float
    awarded_count: int


class ContractorMetrics(BaseModel):
    """Contractor performance metrics."""

    contractor_id: str
    contractor_name: str
    total_bids: int
    won_bids: int
    win_rate_pct: float
    avg_bid_amount_bdt: float
    avg_award_value_bdt: float
    award_count: int


class MarketTrendPoint(BaseModel):
    """Monthly market trend data point."""

    month: str
    tender_count: int
    total_value_bdt: float
    avg_value_bdt: float


class CategoryTrendPoint(BaseModel):
    """Category trend data point."""

    category_id: str
    category_name: str
    sector: Optional[str]
    month: str
    tender_count: int
    total_value_bdt: float
    avg_value_bdt: float


class WarehouseStats(BaseModel):
    """Warehouse data freshness metrics."""

    dim_agencies: int
    dim_contractors: int
    fact_tenders: int
    fact_awards: int
    fact_bids: int


# ── Endpoints ────────────────────────────────────────────────────────


@router.get("/market-overview", response_model=MarketOverviewResponse)
async def get_market_overview(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """Get overall market metrics.

    Returns:
    - Total tenders (all-time)
    - Total tender value (current year)
    - Average tender value
    - Number of awarded tenders
    """
    if not user or not user.get("tenant_id"):
        raise HTTPException(status_code=403, detail="Authentication required")

    overview = await AnalyticsWarehouseService.get_market_overview(db)
    return overview


@router.get("/market-by-agency", response_model=List[AgencyMetrics])
async def get_market_by_agency(
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> list[dict]:
    """Get market metrics by agency.

    Top agencies by tender count, with value and speed metrics.

    Query Parameters:
    - limit: Max agencies to return (default 50)

    Returns:
    - Agency metrics sorted by tender count (descending)
    """
    if not user or not user.get("tenant_id"):
        raise HTTPException(status_code=403, detail="Authentication required")

    results = await AnalyticsWarehouseService.get_market_by_agency(db, limit=limit)
    return results


@router.get("/contractors-performance", response_model=List[ContractorMetrics])
async def get_contractors_performance(
    limit: int = Query(100, ge=1, le=500),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> list[dict]:
    """Get contractor performance metrics.

    Ranked contractors by award count, with win rates and bid metrics.

    Query Parameters:
    - limit: Max contractors to return (default 100)

    Returns:
    - Contractor metrics sorted by award count (descending)
    """
    if not user or not user.get("tenant_id"):
        raise HTTPException(status_code=403, detail="Authentication required")

    results = await AnalyticsWarehouseService.get_contractor_performance(db, limit=limit)
    return results


@router.get("/market-trend", response_model=List[MarketTrendPoint])
async def get_market_trend(
    zone_id: Optional[str] = Query(None, description="Filter by zone (optional)"),
    months: int = Query(12, ge=1, le=36, description="Number of months to analyze"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> list[dict]:
    """Get monthly tender volume and value trends.

    Shows market activity over time for forecasting and analysis.

    Query Parameters:
    - zone_id: Optional zone filter
    - months: Number of months (1-36, default 12)

    Returns:
    - Monthly aggregations sorted by month (ascending)
    """
    if not user or not user.get("tenant_id"):
        raise HTTPException(status_code=403, detail="Authentication required")

    results = await AnalyticsWarehouseService.get_market_trend(db, zone_id=zone_id, months=months)
    return results


@router.get("/category-trends", response_model=List[CategoryTrendPoint])
async def get_category_trends(
    sector: Optional[str] = Query(None, description="Filter by sector (optional)"),
    months: int = Query(12, ge=1, le=36, description="Number of months to analyze"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> list[dict]:
    """Get category/sector trends over time.

    Analyzes market activity by procurement category and sector.

    Query Parameters:
    - sector: Optional sector filter
    - months: Number of months (1-36, default 12)

    Returns:
    - Category metrics sorted by month (descending) then tender count (descending)
    """
    if not user or not user.get("tenant_id"):
        raise HTTPException(status_code=403, detail="Authentication required")

    results = await AnalyticsWarehouseService.get_category_trends(db, sector=sector, months=months)
    return results


@router.get("/warehouse-stats", response_model=WarehouseStats)
async def get_warehouse_stats(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """Get warehouse health metrics.

    Shows row counts for freshness monitoring.

    Returns:
    - Row counts by table (dimensions and facts)
    - Used to verify data is loaded and current
    """
    if not user or not user.get("tenant_id"):
        raise HTTPException(status_code=403, detail="Authentication required")

    stats = await AnalyticsWarehouseService.get_warehouse_stats(db)
    return stats


# ── Real-time metrics (for dashboard refresh) ────────────────────────


@router.get("/live-metrics")
async def get_live_metrics(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """Get all dashboard metrics in one call (cached, <500ms).

    Combines:
    - Market overview
    - Top 10 agencies
    - Top 20 contractors
    - Latest month trend

    Optimized for dashboard initial load.
    """
    if not user or not user.get("tenant_id"):
        raise HTTPException(status_code=403, detail="Authentication required")

    # Run queries in parallel where possible
    overview = await AnalyticsWarehouseService.get_market_overview(db)
    agencies = await AnalyticsWarehouseService.get_market_by_agency(db, limit=10)
    contractors = await AnalyticsWarehouseService.get_contractor_performance(db, limit=20)
    trends = await AnalyticsWarehouseService.get_market_trend(db, months=1)
    stats = await AnalyticsWarehouseService.get_warehouse_stats(db)

    return {
        "overview": overview,
        "top_agencies": agencies,
        "top_contractors": contractors,
        "latest_trend": trends[-1] if trends else None,
        "warehouse": stats,
        "timestamp": str(__import__("datetime").datetime.now(__import__("datetime").timezone.utc)),
    }

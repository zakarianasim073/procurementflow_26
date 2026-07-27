"""Benchmarking API endpoints (T-022: Competitor Analysis)."""

from __future__ import annotations

import logging
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.security import get_current_user
from app.db.base import get_async_session
from app.services.benchmarking_service import BenchmarkingService
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/benchmarking", tags=["benchmarking"])


# ── Response Models ──────────────────────────────────────────────────


class PeerContractor(BaseModel):
    """Peer contractor with similarity metrics."""

    contractor_id: str
    contractor_name: str
    category: Optional[str]
    zone: Optional[str]
    bid_count: int
    award_count: int
    total_contract_value_bdt: float
    completion_rate_pct: float
    similarity_score: int


class WinRateMetrics(BaseModel):
    """Win rate and bid statistics."""

    contractor_id: str
    total_bids: int
    won_bids: int
    award_count: int
    total_award_value: float
    win_rate_pct: float


class BidStrategy(BaseModel):
    """Bid strategy analysis (aggressiveness, patterns)."""

    contractor_id: str
    avg_bid_amount: float
    min_bid_amount: float
    max_bid_amount: float
    bid_volatility: float
    market_avg_bid: float
    bid_success_rate: float
    bid_to_market_ratio: float
    market_position: str  # aggressive, competitive, premium


class AwardMetrics(BaseModel):
    """Award frequency and quality metrics."""

    contractor_id: str
    award_count: int
    avg_award_value: float
    total_award_value: float
    avg_days_to_award: int
    min_days_to_award: int
    max_days_to_award: int
    completion_rate_pct: float
    ongoing_projects: int


class CategoryPerformance(BaseModel):
    """Category-level performance breakdown."""

    category_id: str
    category_name: str
    sector: Optional[str]
    bid_count: int
    won_bids: int
    avg_bid_amount: float
    avg_award_value: float
    award_count: int
    win_rate_pct: float


class MarketRank(BaseModel):
    """Market position and percentile ranking."""

    rank: int
    metric_value: float
    percentile: float
    peer_count: int
    category: Optional[str]
    zone: Optional[str]


class CompetitorProfile(BaseModel):
    """Complete competitor benchmark profile."""

    contractor_id: str
    contractor_name: Optional[str]
    win_rate: WinRateMetrics
    bid_strategy: BidStrategy
    awards: AwardMetrics
    top_categories: List[CategoryPerformance]
    market_rank: MarketRank


# ── Endpoints ────────────────────────────────────────────────────────


@router.get("/contractors/{contractor_id}/peer-group", response_model=List[PeerContractor])
async def get_peer_group(
    contractor_id: str,
    limit: int = Query(5, ge=1, le=20),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> list[dict]:
    """Get peer contractors for competitive comparison.

    Peers matched by category, zone, and similar bid volume.

    Args:
        contractor_id: Target contractor
        limit: Max peers to return (1-20)

    Returns:
        List of peer contractors ranked by similarity score
    """
    if not user or not user.get("tenant_id"):
        raise HTTPException(status_code=403, detail="Authentication required")

    peers = await BenchmarkingService.get_peer_groups(db, contractor_id, limit=limit)
    return peers


@router.get("/contractors/{contractor_id}/win-rate", response_model=WinRateMetrics)
async def get_win_rate(
    contractor_id: str,
    months: int = Query(12, ge=1, le=36),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """Get contractor win rate and bid statistics.

    Win rate = (awarded bids / total bids) * 100

    Args:
        contractor_id: Target contractor
        months: Lookback period (1-36 months, default 12)

    Returns:
        Win rate percentage, bid counts, total award value
    """
    if not user or not user.get("tenant_id"):
        raise HTTPException(status_code=403, detail="Authentication required")

    metrics = await BenchmarkingService.get_contractor_win_rate(db, contractor_id, months=months)
    return metrics


@router.get("/contractors/{contractor_id}/bid-strategy", response_model=BidStrategy)
async def get_bid_strategy(
    contractor_id: str,
    months: int = Query(12, ge=1, le=36),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """Analyze contractor's bidding strategy and market position.

    Compares bid amounts, aggressiveness, and patterns against market average.

    Args:
        contractor_id: Target contractor
        months: Lookback period (1-36 months, default 12)

    Returns:
        Bid strategy metrics (aggressive/competitive/premium positioning)
    """
    if not user or not user.get("tenant_id"):
        raise HTTPException(status_code=403, detail="Authentication required")

    strategy = await BenchmarkingService.get_bid_strategy(db, contractor_id, months=months)
    return strategy


@router.get("/contractors/{contractor_id}/awards", response_model=AwardMetrics)
async def get_awards(
    contractor_id: str,
    months: int = Query(12, ge=1, le=36),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """Get award frequency and quality metrics.

    Includes completion rates, time-to-award, and project status.

    Args:
        contractor_id: Target contractor
        months: Lookback period (1-36 months, default 12)

    Returns:
        Award metrics (frequency, value, timing, completion rate)
    """
    if not user or not user.get("tenant_id"):
        raise HTTPException(status_code=403, detail="Authentication required")

    awards = await BenchmarkingService.get_award_analysis(db, contractor_id, months=months)
    return awards


@router.get(
    "/contractors/{contractor_id}/categories",
    response_model=List[CategoryPerformance]
)
async def get_top_categories(
    contractor_id: str,
    limit: int = Query(5, ge=1, le=20),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> list[dict]:
    """Get contractor's top performing categories/sectors.

    Ranked by award count and win rate.

    Args:
        contractor_id: Target contractor
        limit: Max categories to return (1-20)

    Returns:
        Categories ranked by performance (awards, win rate)
    """
    if not user or not user.get("tenant_id"):
        raise HTTPException(status_code=403, detail="Authentication required")

    categories = await BenchmarkingService.get_category_performance(
        db, contractor_id, top_n=limit
    )
    return categories


@router.get("/contractors/{contractor_id}/market-rank", response_model=MarketRank)
async def get_market_rank(
    contractor_id: str,
    metric: str = Query("win_rate", pattern="^(win_rate|bid_volume|award_value)$"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """Get contractor's market rank among peers.

    Ranked within same category and zone.

    Args:
        contractor_id: Target contractor
        metric: Ranking basis (win_rate, bid_volume, award_value)

    Returns:
        Rank, percentile, peer count
    """
    if not user or not user.get("tenant_id"):
        raise HTTPException(status_code=403, detail="Authentication required")

    rank = await BenchmarkingService.get_market_rank(db, contractor_id, metric=metric)
    return rank


@router.get("/contractors/{contractor_id}/profile", response_model=CompetitorProfile)
async def get_full_profile(
    contractor_id: str,
    months: int = Query(12, ge=1, le=36),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """Get complete competitor benchmark profile.

    Combines win rate, bid strategy, awards, and market rank in one call.

    Args:
        contractor_id: Target contractor
        months: Lookback period for metrics (1-36 months, default 12)

    Returns:
        Comprehensive profile (all benchmarking metrics combined)
    """
    if not user or not user.get("tenant_id"):
        raise HTTPException(status_code=403, detail="Authentication required")

    # Fetch all metrics in parallel
    win_rate = await BenchmarkingService.get_contractor_win_rate(db, contractor_id, months=months)
    bid_strategy = await BenchmarkingService.get_bid_strategy(db, contractor_id, months=months)
    awards = await BenchmarkingService.get_award_analysis(db, contractor_id, months=months)
    categories = await BenchmarkingService.get_category_performance(db, contractor_id, top_n=5)
    market_rank = await BenchmarkingService.get_market_rank(db, contractor_id)

    return {
        "contractor_id": contractor_id,
        "contractor_name": None,  # Would need to fetch from dim_contractors
        "win_rate": win_rate,
        "bid_strategy": bid_strategy,
        "awards": awards,
        "top_categories": categories,
        "market_rank": market_rank,
    }

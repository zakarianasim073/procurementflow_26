"""Benchmarking Service (T-022): Competitor performance analysis and peer grouping."""

from __future__ import annotations

import logging
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class BenchmarkingService:
    """Peer group analysis, win rate calculation, and performance ranking."""

    @staticmethod
    async def get_peer_groups(
        db: AsyncSession, contractor_id: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get peer contractors (same category + zone, similar bid volume).

        Args:
            contractor_id: Target contractor to find peers for
            limit: Max peers to return

        Returns:
            List of peer contractors with similarity score
        """
        result = await db.execute(
            text("""
                WITH target_contractor AS (
                    SELECT c.contractor_id, c.category, c.zone, c.bid_count
                    FROM dim_contractors c
                    WHERE c.contractor_id = :contractor_id
                ),
                peer_candidates AS (
                    SELECT
                        c.contractor_id,
                        c.contractor_name,
                        c.category,
                        c.zone,
                        c.bid_count,
                        c.award_count,
                        c.total_contract_value_bdt,
                        c.completion_rate_pct,
                        -- Similarity score: category + zone match, bid volume proximity
                        CASE
                            WHEN c.category = tc.category AND c.zone = tc.zone THEN 10
                            WHEN c.category = tc.category OR c.zone = tc.zone THEN 5
                            ELSE 0
                        END +
                        -- Bid volume similarity (lower absolute difference = higher score)
                        GREATEST(0, 10 - ABS(c.bid_count - tc.bid_count)::DECIMAL /
                            NULLIF(tc.bid_count, 0) * 10)::INT as similarity_score
                    FROM dim_contractors c, target_contractor tc
                    WHERE c.contractor_id != tc.contractor_id
                )
                SELECT
                    contractor_id,
                    contractor_name,
                    category,
                    zone,
                    bid_count,
                    award_count,
                    total_contract_value_bdt,
                    completion_rate_pct,
                    similarity_score
                FROM peer_candidates
                WHERE similarity_score > 0
                ORDER BY similarity_score DESC
                LIMIT :limit
            """),
            {"contractor_id": contractor_id, "limit": limit},
        )

        return [
            {
                "contractor_id": row[0],
                "contractor_name": row[1],
                "category": row[2],
                "zone": row[3],
                "bid_count": row[4],
                "award_count": row[5],
                "total_contract_value_bdt": float(row[6] or 0),
                "completion_rate_pct": float(row[7] or 0),
                "similarity_score": row[8],
            }
            for row in result.fetchall()
        ]

    @staticmethod
    async def get_contractor_win_rate(
        db: AsyncSession, contractor_id: str, months: int = 12
    ) -> Dict[str, Any]:
        """Calculate contractor win rate (% awards / total bids).

        Args:
            contractor_id: Target contractor
            months: Lookback period

        Returns:
            Win rate metrics (%, count, trend)
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=months * 30)

        result = await db.execute(
            text("""
                WITH contractor_activity AS (
                    SELECT
                        COUNT(DISTINCT fb.bid_id) as total_bids,
                        COUNT(DISTINCT CASE WHEN fb.is_winner THEN fb.bid_id END) as won_bids,
                        COUNT(DISTINCT fa.award_id) as award_count,
                        SUM(fa.award_value_bdt) as total_award_value
                    FROM fact_bids fb
                    LEFT JOIN fact_awards fa ON fb.tender_id = fa.tender_id
                        AND fb.contractor_id = fa.contractor_id
                    WHERE fb.contractor_id = :contractor_id
                        AND fb.bid_date >= :cutoff_date
                )
                SELECT
                    total_bids,
                    won_bids,
                    award_count,
                    total_award_value,
                    CASE
                        WHEN total_bids > 0 THEN (won_bids::DECIMAL / total_bids * 100)
                        ELSE 0
                    END as win_rate_pct
                FROM contractor_activity
            """),
            {"contractor_id": contractor_id, "cutoff_date": cutoff},
        )

        row = result.first()
        if not row:
            return {
                "contractor_id": contractor_id,
                "total_bids": 0,
                "won_bids": 0,
                "award_count": 0,
                "total_award_value": 0.0,
                "win_rate_pct": 0.0,
            }

        return {
            "contractor_id": contractor_id,
            "total_bids": row[0] or 0,
            "won_bids": row[1] or 0,
            "award_count": row[2] or 0,
            "total_award_value": float(row[3] or 0),
            "win_rate_pct": float(row[4] or 0),
        }

    @staticmethod
    async def get_bid_strategy(
        db: AsyncSession, contractor_id: str, months: int = 12
    ) -> Dict[str, Any]:
        """Analyze contractor's bidding strategy.

        Metrics: bid amount vs market average, bid frequency, win correlation

        Args:
            contractor_id: Target contractor
            months: Lookback period

        Returns:
            Bid strategy metrics (avg bid, market position, patterns)
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=months * 30)

        result = await db.execute(
            text("""
                WITH contractor_bids AS (
                    SELECT
                        fb.bid_amount_bdt,
                        fb.is_winner,
                        ft.tender_value_bdt,
                        fb.bid_date,
                        ROW_NUMBER() OVER (ORDER BY fb.bid_date) as bid_sequence
                    FROM fact_bids fb
                    JOIN fact_tenders ft ON fb.tender_id = ft.tender_id
                    WHERE fb.contractor_id = :contractor_id
                        AND fb.bid_date >= :cutoff_date
                ),
                market_stats AS (
                    SELECT
                        AVG(bid_amount_bdt) as market_avg_bid,
                        STDDEV(bid_amount_bdt) as market_stddev_bid
                    FROM fact_bids fb
                    WHERE fb.bid_date >= :cutoff_date
                )
                SELECT
                    AVG(cb.bid_amount_bdt) as avg_bid_amount,
                    MIN(cb.bid_amount_bdt) as min_bid_amount,
                    MAX(cb.bid_amount_bdt) as max_bid_amount,
                    STDDEV(cb.bid_amount_bdt) as bid_volatility,
                    (SELECT market_avg_bid FROM market_stats) as market_avg_bid,
                    (SELECT market_stddev_bid FROM market_stats) as market_stddev_bid,
                    CASE WHEN COUNT(*) > 0
                        THEN (SUM(CASE WHEN cb.is_winner THEN 1 ELSE 0 END)::DECIMAL / COUNT(*) * 100)
                        ELSE 0
                    END as bid_success_rate,
                    -- Bid aggressiveness: avg bid vs market avg (lower = more aggressive)
                    CASE WHEN (SELECT market_avg_bid FROM market_stats) > 0
                        THEN (AVG(cb.bid_amount_bdt) / (SELECT market_avg_bid FROM market_stats) * 100)
                        ELSE 0
                    END as bid_to_market_ratio
                FROM contractor_bids cb
            """),
            {"contractor_id": contractor_id, "cutoff_date": cutoff},
        )

        row = result.first()
        if not row:
            return {
                "contractor_id": contractor_id,
                "avg_bid_amount": 0.0,
                "bid_volatility": 0.0,
                "market_position": "insufficient_data",
            }

        market_avg = float(row[4] or 1)
        bid_to_market = float(row[7] or 0)

        return {
            "contractor_id": contractor_id,
            "avg_bid_amount": float(row[0] or 0),
            "min_bid_amount": float(row[1] or 0),
            "max_bid_amount": float(row[2] or 0),
            "bid_volatility": float(row[3] or 0),
            "market_avg_bid": market_avg,
            "bid_success_rate": float(row[6] or 0),
            "bid_to_market_ratio": bid_to_market,
            "market_position": (
                "aggressive" if bid_to_market < 90
                else "competitive" if bid_to_market < 110
                else "premium"
            ),
        }

    @staticmethod
    async def get_award_analysis(
        db: AsyncSession, contractor_id: str, months: int = 12
    ) -> Dict[str, Any]:
        """Analyze award frequency, timing, and value patterns.

        Args:
            contractor_id: Target contractor
            months: Lookback period

        Returns:
            Award metrics (frequency, avg value, time to award, completion rate)
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=months * 30)

        result = await db.execute(
            text("""
                WITH awards AS (
                    SELECT
                        fa.award_id,
                        fa.award_value_bdt,
                        fa.days_to_award,
                        fa.completion_status,
                        fa.award_date,
                        ft.tender_value_bdt
                    FROM fact_awards fa
                    JOIN fact_tenders ft ON fa.tender_id = ft.tender_id
                    WHERE fa.contractor_id = :contractor_id
                        AND fa.award_date >= :cutoff_date
                )
                SELECT
                    COUNT(DISTINCT award_id) as award_count,
                    AVG(award_value_bdt) as avg_award_value,
                    SUM(award_value_bdt) as total_award_value,
                    AVG(days_to_award) as avg_days_to_award,
                    MIN(days_to_award) as min_days_to_award,
                    MAX(days_to_award) as max_days_to_award,
                    COUNT(CASE WHEN completion_status = 'completed' THEN 1 END)::DECIMAL /
                        NULLIF(COUNT(*), 0) * 100 as completion_rate_pct,
                    COUNT(CASE WHEN completion_status = 'ongoing' THEN 1 END) as ongoing_projects
                FROM awards
            """),
            {"contractor_id": contractor_id, "cutoff_date": cutoff},
        )

        row = result.first()
        if not row:
            return {
                "contractor_id": contractor_id,
                "award_count": 0,
                "avg_award_value": 0.0,
                "total_award_value": 0.0,
                "avg_days_to_award": 0,
                "completion_rate_pct": 0.0,
            }

        return {
            "contractor_id": contractor_id,
            "award_count": row[0] or 0,
            "avg_award_value": float(row[1] or 0),
            "total_award_value": float(row[2] or 0),
            "avg_days_to_award": int(row[3] or 0),
            "min_days_to_award": int(row[4] or 0),
            "max_days_to_award": int(row[5] or 0),
            "completion_rate_pct": float(row[6] or 0),
            "ongoing_projects": row[7] or 0,
        }

    @staticmethod
    async def get_category_performance(
        db: AsyncSession, contractor_id: str, top_n: int = 5
    ) -> List[Dict[str, Any]]:
        """Top performing categories for a contractor.

        Args:
            contractor_id: Target contractor
            top_n: Number of categories to return

        Returns:
            Category performance (win rate, bid count, avg value)
        """
        result = await db.execute(
            text("""
                WITH category_stats AS (
                    SELECT
                        dc.category_id,
                        dc.category_name,
                        dc.sector,
                        COUNT(DISTINCT fb.bid_id) as bid_count,
                        COUNT(DISTINCT CASE WHEN fb.is_winner THEN fb.bid_id END) as won_bids,
                        AVG(fb.bid_amount_bdt) as avg_bid_amount,
                        AVG(fa.award_value_bdt) as avg_award_value,
                        COUNT(DISTINCT fa.award_id) as award_count
                    FROM fact_bids fb
                    JOIN fact_tenders ft ON fb.tender_id = ft.tender_id
                    JOIN dim_categories dc ON ft.category_id = dc.category_id
                    LEFT JOIN fact_awards fa ON fb.tender_id = fa.tender_id
                        AND fb.contractor_id = fa.contractor_id
                    WHERE fb.contractor_id = :contractor_id
                    GROUP BY dc.category_id, dc.category_name, dc.sector
                )
                SELECT
                    category_id,
                    category_name,
                    sector,
                    bid_count,
                    won_bids,
                    avg_bid_amount,
                    avg_award_value,
                    award_count,
                    (won_bids::DECIMAL / NULLIF(bid_count, 0) * 100) as win_rate_pct
                FROM category_stats
                ORDER BY award_count DESC
                LIMIT :limit
            """),
            {"contractor_id": contractor_id, "limit": top_n},
        )

        return [
            {
                "category_id": row[0],
                "category_name": row[1],
                "sector": row[2],
                "bid_count": row[3],
                "won_bids": row[4],
                "avg_bid_amount": float(row[5] or 0),
                "avg_award_value": float(row[6] or 0),
                "award_count": row[7],
                "win_rate_pct": float(row[8] or 0),
            }
            for row in result.fetchall()
        ]

    @staticmethod
    async def get_market_rank(
        db: AsyncSession, contractor_id: str, metric: str = "win_rate"
    ) -> Dict[str, Any]:
        """Rank contractor among all contractors in their category/zone.

        Args:
            contractor_id: Target contractor
            metric: Ranking metric (win_rate, bid_volume, award_value)

        Returns:
            Market rank (position, percentile, category leaders)
        """
        # Get contractor's category/zone first
        contractor_info = await db.execute(
            text("""
                SELECT category, zone FROM dim_contractors
                WHERE contractor_id = :contractor_id
            """),
            {"contractor_id": contractor_id},
        )
        cat_zone = contractor_info.first()
        if not cat_zone:
            return {
                "rank": 0,
                "metric_value": 0,
                "percentile": 0,
                "peer_count": 0,
                "category": None,
                "zone": None,
            }

        category, zone = cat_zone

        # Rank based on metric
        if metric == "win_rate":
            result = await db.execute(
                text("""
                    WITH ranked_contractors AS (
                        SELECT
                            c.contractor_id,
                            (COUNT(DISTINCT CASE WHEN fb.is_winner THEN fb.bid_id END)::DECIMAL /
                             NULLIF(COUNT(DISTINCT fb.bid_id), 0) * 100) as metric_value,
                            ROW_NUMBER() OVER (ORDER BY
                                COUNT(DISTINCT CASE WHEN fb.is_winner THEN fb.bid_id END)::DECIMAL /
                                NULLIF(COUNT(DISTINCT fb.bid_id), 0) DESC
                            ) as rank,
                            COUNT(*) OVER () as total_count
                        FROM dim_contractors c
                        LEFT JOIN fact_bids fb ON c.contractor_id = fb.contractor_id
                        WHERE c.category = :category AND c.zone = :zone
                        GROUP BY c.contractor_id
                    )
                    SELECT rank, metric_value, total_count FROM ranked_contractors
                    WHERE contractor_id = :contractor_id
                """),
                {"contractor_id": contractor_id, "category": category, "zone": zone},
            )
        else:
            # Default to bid volume
            result = await db.execute(
                text("""
                    WITH ranked_contractors AS (
                        SELECT
                            c.contractor_id,
                            COUNT(DISTINCT fb.bid_id) as metric_value,
                            ROW_NUMBER() OVER (ORDER BY COUNT(DISTINCT fb.bid_id) DESC) as rank,
                            COUNT(*) OVER () as total_count
                        FROM dim_contractors c
                        LEFT JOIN fact_bids fb ON c.contractor_id = fb.contractor_id
                        WHERE c.category = :category AND c.zone = :zone
                        GROUP BY c.contractor_id
                    )
                    SELECT rank, metric_value, total_count FROM ranked_contractors
                    WHERE contractor_id = :contractor_id
                """),
                {"contractor_id": contractor_id, "category": category, "zone": zone},
            )

        row = result.first()
        if not row:
            return {"rank": 0, "metric_value": 0, "percentile": 0, "peer_count": 0, "category": category, "zone": zone}

        rank, metric_value, total = row
        percentile = (total - rank) / total * 100 if total > 0 else 0

        return {
            "rank": rank or 0,
            "metric_value": float(metric_value or 0),
            "percentile": percentile,
            "peer_count": total or 0,
            "category": category,
            "zone": zone,
        }

"""Analytics Warehouse Service (T-020).

Handles ETL refresh and OLAP queries for analytics dashboards.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import select, text, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import (
    DimAgencies,
    DimZones,
    DimCategories,
    DimContractors,
    FactTenders,
    FactAwards,
    FactBids,
)

logger = logging.getLogger(__name__)


class AnalyticsWarehouseService:
    """OLAP warehouse with incremental refresh and aggregation queries."""

    @staticmethod
    async def refresh_dimensions(db: AsyncSession) -> Dict[str, int]:
        """Refresh dimension tables from source data (incremental).

        Returns: {table_name: rows_inserted}
        """
        refresh_results = {}

        # Refresh dim_agencies from agencies (real source table)
        result = await db.execute(
            text("""
                INSERT INTO dim_agencies (
                    agency_id, agency_code, agency_name, division, region,
                    is_active, last_tender_date, total_spend_bdt, tender_count
                )
                SELECT
                    a.id, a.agency_code, a.agency_name, a.ministry, NULL,
                    TRUE, NULL, 0, 0
                FROM agencies a
                ON CONFLICT (agency_id) DO UPDATE SET
                    agency_name = EXCLUDED.agency_name,
                    division = EXCLUDED.division,
                    updated_at = NOW()
            """)
        )
        refresh_results["dim_agencies"] = result.rowcount

        # Refresh dim_contractors from canonical_contractors (contractors is
        # unpopulated in this deployment; canonical_contractor_id is the ID
        # space fact_awards.contractor_id must match).
        result = await db.execute(
            text("""
                INSERT INTO dim_contractors (
                    contractor_id, contractor_name, registration_number,
                    category, zone, bid_count, award_count, total_contract_value_bdt
                )
                SELECT c.canonical_contractor_id, LEFT(c.display_name, 255), NULL,
                       NULL, NULL, c.total_bids, c.total_wins, c.last_5yr_awarded_amount_bdt
                FROM canonical_contractors c
                WHERE c.display_name IS NOT NULL AND c.display_name <> ''
                ON CONFLICT (contractor_id) DO UPDATE SET
                    contractor_name = EXCLUDED.contractor_name,
                    award_count = EXCLUDED.award_count,
                    total_contract_value_bdt = EXCLUDED.total_contract_value_bdt,
                    updated_at = NOW()
            """)
        )
        refresh_results["dim_contractors"] = result.rowcount

        await db.commit()
        return refresh_results

    @staticmethod
    async def refresh_facts(db: AsyncSession, hours_back: int = 24) -> Dict[str, int]:
        """Refresh fact tables incrementally (only new/updated records).

        Args:
            hours_back: Only sync tenders modified in last N hours

        Returns: {table_name: rows_inserted}
        """
        refresh_results = {}
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        cutoff_naive = cutoff_time.replace(tzinfo=None)

        # Refresh fact_tenders from canonical_tenders — the populated
        # derived-identity table (procurement_lifecycle, the original
        # source, is unpopulated in this deployment).
        result = await db.execute(
            text("""
                INSERT INTO fact_tenders (
                    tender_id, agency_id, zone_id, category_id,
                    tender_value_bdt, estimated_value_bdt, procurement_method,
                    tender_type, status, published_date, deadline_date,
                    award_date, completion_date, bid_count, duration_days
                )
                SELECT
                    md5(ct.canonical_package_key),
                    dc.agency_id,
                    NULL, NULL,
                    CASE WHEN ct.estimated_cost_bdt > 0 AND ct.estimated_cost_bdt < 1e13 THEN ct.estimated_cost_bdt END,
                    CASE WHEN ct.estimated_cost_bdt > 0 AND ct.estimated_cost_bdt < 1e13 THEN ct.estimated_cost_bdt END,
                    NULL,
                    'canonical',
                    'identified',
                    NULL, NULL, NULL, NULL, 0, NULL
                FROM canonical_tenders ct
                LEFT JOIN dim_agencies dc ON dc.agency_code = ct.agency_code
                WHERE ct.rebuilt_at > :cutoff
                ON CONFLICT (tender_id) DO UPDATE SET
                    tender_value_bdt = EXCLUDED.tender_value_bdt,
                    updated_at = NOW()
            """),
            {"cutoff": cutoff_naive},
        )
        refresh_results["fact_tenders"] = result.rowcount

        # Refresh fact_awards from canonical_awards, linked to fact_tenders by
        # the same canonical_package_key hash and to dim_contractors by id.
        result = await db.execute(
            text("""
                INSERT INTO fact_awards (
                    award_id, tender_id, contractor_id, award_value_bdt,
                    award_date, completion_status, days_to_award
                )
                SELECT DISTINCT ON (ca.canonical_award_id)
                    ca.canonical_award_id, md5(ca.canonical_package_key), dc.contractor_id,
                    CASE WHEN ca.award_amount_bdt > 0 AND ca.award_amount_bdt < 1e13 THEN ca.award_amount_bdt END,
                    ca.award_date, 'awarded', NULL
                FROM canonical_awards ca
                JOIN fact_tenders ft ON ft.tender_id = md5(ca.canonical_package_key)
                LEFT JOIN dim_contractors dc ON dc.contractor_id = ca.canonical_contractor_id
                WHERE ca.rebuilt_at > :cutoff
                ON CONFLICT (award_id) DO UPDATE SET
                    award_value_bdt = EXCLUDED.award_value_bdt,
                    award_date = EXCLUDED.award_date
            """),
            {"cutoff": cutoff_naive},
        )
        refresh_results["fact_awards"] = result.rowcount

        # fact_bids: no per-bid amounts exist in any source table (opening
        # reports carry bidder names only) — deliberately left empty.
        refresh_results["fact_bids"] = 0

        await db.commit()
        return refresh_results

    @staticmethod
    async def refresh_materialized_views(db: AsyncSession) -> Dict[str, bool]:
        """Refresh all materialized views (full refresh).

        Returns: {view_name: success}
        """
        views = [
            "vw_market_by_agency",
            "vw_market_by_zone",
            "vw_contractor_performance",
            "vw_tender_volume_monthly",
            "vw_category_trends",
        ]

        results = {}
        for view_name in views:
            try:
                # CONCURRENTLY requires a unique index on the view, which
                # none of these have — plain REFRESH takes a brief lock but
                # works unconditionally.
                await db.execute(text(f"REFRESH MATERIALIZED VIEW {view_name}"))
                await db.commit()
                results[view_name] = True
                logger.info(f"Refreshed materialized view: {view_name}")
            except Exception as e:
                await db.rollback()
                results[view_name] = False
                logger.error(f"Failed to refresh {view_name}: {e}")

        return results

    @staticmethod
    async def get_market_overview(db: AsyncSession) -> Dict[str, Any]:
        """Get overall market metrics from the populated operational tables.

        The warehouse tender facts intentionally have no published dates for
        canonical records, so filtering them to the current year returned an
        all-zero dashboard even though PostgreSQL contained the full lifecycle
        dataset.  The operational lifecycle is the authoritative, populated
        source for these live widgets.
        """
        result = await db.execute(
            text("""
                SELECT
                    (SELECT COUNT(*) FROM procurement_tenders) AS total_tenders,
                    COALESCE(SUM(estimated_cost_bdt)
                        FILTER (WHERE estimated_cost_bdt BETWEEN 1 AND 1e13), 0)
                        AS total_value_bdt,
                    COALESCE(AVG(estimated_cost_bdt)
                        FILTER (WHERE estimated_cost_bdt BETWEEN 1 AND 1e13), 0)
                        AS avg_value_bdt,
                    COUNT(*) FILTER (
                        WHERE award_amount_bdt > 0 OR winner IS NOT NULL
                    ) AS awarded_count
                FROM procurement_lifecycle
            """)
        )
        row = result.first()
        if not row:
            return {}

        return {
            "total_tenders": row[0] or 0,
            "total_value_bdt": float(row[1] or 0),
            "avg_value_bdt": float(row[2] or 0),
            "awarded_count": row[3] or 0,
        }

    @staticmethod
    async def get_market_by_agency(
        db: AsyncSession, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get agency metrics from operational tender/lifecycle data."""
        result = await db.execute(
            text("""
                WITH tender_counts AS (
                    SELECT COALESCE(NULLIF(TRIM(agency_code), ''), 'UNKNOWN') AS agency_code,
                           COUNT(*) AS tender_count
                    FROM procurement_tenders
                    GROUP BY 1
                ),
                lifecycle AS (
                    SELECT COALESCE(NULLIF(TRIM(agency_code), ''), 'UNKNOWN') AS agency_code,
                           COALESCE(SUM(estimated_cost_bdt)
                               FILTER (WHERE estimated_cost_bdt BETWEEN 1 AND 1e13), 0) AS total_value_bdt,
                           COALESCE(AVG(estimated_cost_bdt)
                               FILTER (WHERE estimated_cost_bdt BETWEEN 1 AND 1e13), 0) AS avg_value_bdt,
                           COUNT(*) FILTER (
                               WHERE award_amount_bdt > 0 OR winner IS NOT NULL
                           ) AS awarded_count
                    FROM procurement_lifecycle
                    GROUP BY 1
                )
                SELECT
                    COALESCE(da.agency_id::text, md5(tc.agency_code)),
                    tc.agency_code,
                    COALESCE(da.agency_name, tc.agency_code),
                    tc.tender_count,
                    COALESCE(l.total_value_bdt, 0),
                    COALESCE(l.avg_value_bdt, 0),
                    0,
                    COALESCE(l.awarded_count, 0)
                FROM tender_counts tc
                LEFT JOIN lifecycle l USING (agency_code)
                LEFT JOIN dim_agencies da ON da.agency_code = tc.agency_code
                ORDER BY tc.tender_count DESC
                LIMIT :limit
            """),
            {"limit": limit},
        )

        return [
            {
                "agency_id": row[0],
                "agency_code": row[1],
                "agency_name": row[2],
                "tender_count": row[3],
                "total_value_bdt": float(row[4] or 0),
                "avg_value_bdt": float(row[5] or 0),
                "avg_duration_days": float(row[6] or 0),
                "awarded_count": row[7],
            }
            for row in result.fetchall()
        ]

    @staticmethod
    async def get_contractor_performance(
        db: AsyncSession, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get contractor performance from populated lifecycle awards.

        Per-bid participation is not available for every historic record, so
        wins are used as the honest minimum bid count and win rate.
        """
        result = await db.execute(
            text("""
                SELECT
                    md5(TRIM(winner)) AS contractor_id,
                    TRIM(winner) AS contractor_name,
                    COUNT(*) AS total_bids,
                    COUNT(*) AS won_bids,
                    100.0 AS win_rate_pct,
                    0.0 AS avg_bid_amount_bdt,
                    COALESCE(AVG(award_amount_bdt)
                        FILTER (WHERE award_amount_bdt BETWEEN 1 AND 1e13), 0)
                        AS avg_award_value_bdt,
                    COUNT(*) AS award_count
                FROM procurement_lifecycle
                WHERE winner IS NOT NULL AND TRIM(winner) <> ''
                GROUP BY TRIM(winner)
                ORDER BY award_count DESC
                LIMIT :limit
            """),
            {"limit": limit},
        )

        return [
            {
                "contractor_id": row[0],
                "contractor_name": row[1],
                "total_bids": row[2],
                "won_bids": row[3],
                "win_rate_pct": float(row[4] or 0),
                "avg_bid_amount_bdt": float(row[5] or 0),
                "avg_award_value_bdt": float(row[6] or 0),
                "award_count": row[7],
            }
            for row in result.fetchall()
        ]

    @staticmethod
    async def get_market_trend(
        db: AsyncSession, zone_id: Optional[str] = None, months: int = 12
    ) -> List[Dict[str, Any]]:
        """Get monthly tender volume trend."""
        result = await db.execute(
            text("""
                SELECT
                    month,
                    tender_count,
                    total_value_bdt,
                    avg_value_bdt
                FROM vw_tender_volume_monthly
                WHERE month >= NOW()::DATE - INTERVAL '1 month' * :months
                    AND (CAST(:zone_id AS text) IS NULL OR zone_id = CAST(:zone_id AS text))
                ORDER BY month ASC
            """),
            {"months": months, "zone_id": zone_id},
        )

        return [
            {
                "month": str(row[0]),
                "tender_count": row[1],
                "total_value_bdt": float(row[2] or 0),
                "avg_value_bdt": float(row[3] or 0),
            }
            for row in result.fetchall()
        ]

    @staticmethod
    async def get_category_trends(
        db: AsyncSession, sector: Optional[str] = None, months: int = 12
    ) -> List[Dict[str, Any]]:
        """Get category/sector trends over time."""
        result = await db.execute(
            text("""
                SELECT
                    category_id,
                    category_name,
                    sector,
                    month,
                    tender_count,
                    total_value_bdt,
                    avg_value_bdt
                FROM vw_category_trends
                WHERE month >= NOW()::DATE - INTERVAL '1 month' * :months
                    AND (CAST(:sector AS text) IS NULL OR sector = CAST(:sector AS text))
                ORDER BY month DESC, tender_count DESC
            """),
            {"months": months, "sector": sector},
        )

        return [
            {
                "category_id": row[0] or "Unknown",
                "category_name": row[1] or "Unknown",
                "sector": row[2],
                "month": str(row[3]),
                "tender_count": row[4],
                "total_value_bdt": float(row[5] or 0),
                "avg_value_bdt": float(row[6] or 0),
            }
            for row in result.fetchall()
        ]

    @staticmethod
    async def get_warehouse_stats(db: AsyncSession) -> Dict[str, int]:
        """Get warehouse row counts and health metrics."""
        stats = {}

        for table in [
            ("dim_agencies", DimAgencies),
            ("dim_contractors", DimContractors),
            ("fact_tenders", FactTenders),
            ("fact_awards", FactAwards),
            ("fact_bids", FactBids),
        ]:
            count = await db.scalar(select(func.count()).select_from(table[1]))
            stats[table[0]] = count or 0

        return stats

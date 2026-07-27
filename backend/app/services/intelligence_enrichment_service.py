"""
Intelligence Enrichment Service
Enriches contractor, agency, and market intelligence with calculated metrics.
Fills gaps in data and calculates derived metrics for knowledge platform.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.intelligence_base import IntelligenceBaseService

logger = logging.getLogger(__name__)


class IntelligenceEnrichmentService(IntelligenceBaseService):
    """Enriches intelligence data with derived metrics and missing values."""

    async def enrich_all_intelligence(self) -> Dict[str, Any]:
        """
        Comprehensive intelligence enrichment:
        1. Calculate contractor performance metrics
        2. Enrich agency intelligence
        3. Enrich zone intelligence
        4. Calculate discount patterns
        5. Populate missing contractor DNA fields
        """
        results = {}

        try:
            results["contractors"] = await self._enrich_contractors()
            results["agencies"] = await self._enrich_agencies()
            results["zones"] = await self._enrich_zones()
            results["patterns"] = await self._enrich_discount_patterns()
            results["awards"] = await self._enrich_award_intelligence()
            results["timestamp"] = datetime.now(timezone.utc).isoformat()
            logger.info(f"Intelligence enrichment complete: {results}")
        except Exception as e:
            logger.error(f"Intelligence enrichment failed: {e}")
            results["error"] = str(e)

        return results

    async def _enrich_contractors(self) -> Dict[str, Any]:
        """Enrich contractor intelligence with performance metrics."""
        # Update contractor_dna with calculated performance metrics
        await self.session.execute(text("""
            UPDATE contractor_dna SET
                -- Win rate: percentage of bids that became awards
                win_rate = LEAST(100.0, GREATEST(0.0,
                    COALESCE(
                        (total_contracts::float / NULLIF(total_contracts + lost_bids_count, 0) * 100.0),
                        (total_contracts::float / GREATEST(total_contracts, 1) * 100.0)
                    )
                )),

                -- Completion rate: percentage of awarded contracts completed
                completion_rate = LEAST(100.0, GREATEST(0.0,
                    (completed_contracts::float / GREATEST(total_contracts, 1) * 100.0)
                )),

                -- On-time rate: percentage of contracts delivered on schedule
                on_time_rate = LEAST(100.0, GREATEST(0.0,
                    (on_time_contracts::float / GREATEST(total_contracts, 1) * 100.0)
                )),

                -- Average delay in days for overdue contracts
                avg_delay_days = GREATEST(0.0, avg_delay_days),

                -- Update health score based on new metrics
                health_score = LEAST(1.0, GREATEST(0.2,
                    0.2 +
                    (COALESCE(total_contracts, 0)::float / GREATEST(COALESCE(total_contracts, 1), 1)) * 0.15 +
                    (total_amount_bdt::float / GREATEST(total_amount_bdt, 1000000)) * 0.15 +
                    ((LEAST(100.0, GREATEST(0.0, (completed_contracts::float / GREATEST(total_contracts, 1) * 100.0))) / 100.0)) * 0.25 +
                    ((LEAST(100.0, GREATEST(0.0, (on_time_contracts::float / GREATEST(total_contracts, 1) * 100.0))) / 100.0)) * 0.25 +
                    (GREATEST(0.0, (1.0 - NULLIF(avg_npp, 0))) * 0.2)
                )),
                updated_at = now()
            WHERE total_contracts > 0
        """))

        count = await self.session.scalar(text(
            "SELECT COUNT(*) FROM contractor_dna WHERE total_contracts > 0"
        ))

        await self.session.flush()
        return {"enriched_contractors": count or 0, "fields": [
            "win_rate", "completion_rate", "on_time_rate", "avg_delay_days", "health_score"
        ]}

    async def _enrich_agencies(self) -> Dict[str, Any]:
        """Enrich agency intelligence with market data."""
        await self.session.execute(text("""
            UPDATE agency_intelligence SET
                total_contracts = (
                    SELECT COUNT(*) FROM procurement_lifecycle
                    WHERE agency_code = agency_intelligence.agency_code
                ),
                total_amount_bdt = (
                    SELECT COALESCE(SUM(award_amount_bdt), 0)::float
                    FROM procurement_lifecycle
                    WHERE agency_code = agency_intelligence.agency_code
                ),
                avg_npp = (
                    SELECT COALESCE(AVG(NULLIF(npp_ratio, 0)), 0)::float
                    FROM procurement_lifecycle
                    WHERE agency_code = agency_intelligence.agency_code
                ),
                npp_trend = CASE
                    WHEN (
                        SELECT COALESCE(AVG(NULLIF(npp_ratio, 0)), 0)::float
                        FROM procurement_lifecycle
                        WHERE agency_code = agency_intelligence.agency_code
                        AND award_date >= now()::date - interval '180 days'
                    ) > (
                        SELECT COALESCE(AVG(NULLIF(npp_ratio, 0)), 0)::float
                        FROM procurement_lifecycle
                        WHERE agency_code = agency_intelligence.agency_code
                        AND award_date < now()::date - interval '180 days'
                    ) THEN 'increasing'
                    WHEN (
                        SELECT COALESCE(AVG(NULLIF(npp_ratio, 0)), 0)::float
                        FROM procurement_lifecycle
                        WHERE agency_code = agency_intelligence.agency_code
                        AND award_date >= now()::date - interval '180 days'
                    ) < (
                        SELECT COALESCE(AVG(NULLIF(npp_ratio, 0)), 0)::float
                        FROM procurement_lifecycle
                        WHERE agency_code = agency_intelligence.agency_code
                        AND award_date < now()::date - interval '180 days'
                    ) THEN 'decreasing'
                    ELSE 'stable'
                END,
                preferred_method = (
                    SELECT procurement_method FROM procurement_lifecycle
                    WHERE agency_code = agency_intelligence.agency_code
                    GROUP BY procurement_method
                    ORDER BY COUNT(*) DESC
                    LIMIT 1
                ),
                updated_at = now()
            WHERE EXISTS (
                SELECT 1 FROM procurement_lifecycle
                WHERE agency_code = agency_intelligence.agency_code
            )
        """))

        count = await self.session.scalar(text(
            "SELECT COUNT(*) FROM agency_intelligence WHERE total_contracts > 0"
        ))

        await self.session.flush()
        return {"enriched_agencies": count or 0, "fields": [
            "total_contracts", "total_amount_bdt", "avg_npp", "npp_trend", "preferred_method"
        ]}

    async def _enrich_zones(self) -> Dict[str, Any]:
        """Enrich zone intelligence with regional market data."""
        await self.session.execute(text("""
            UPDATE zone_intelligence SET
                total_contracts = (
                    SELECT COUNT(*) FROM procurement_lifecycle
                    WHERE zone_name = zone_intelligence.zone_name
                ),
                total_amount_bdt = (
                    SELECT COALESCE(SUM(award_amount_bdt), 0)::float
                    FROM procurement_lifecycle
                    WHERE zone_name = zone_intelligence.zone_name
                ),
                active_agencies = (
                    SELECT COUNT(DISTINCT agency_code) FROM procurement_lifecycle
                    WHERE zone_name = zone_intelligence.zone_name
                ),
                avg_npp = (
                    SELECT COALESCE(AVG(NULLIF(npp_ratio, 0)), 0)::float
                    FROM procurement_lifecycle
                    WHERE zone_name = zone_intelligence.zone_name
                ),
                updated_at = now()
            WHERE EXISTS (
                SELECT 1 FROM procurement_lifecycle
                WHERE zone_name = zone_intelligence.zone_name
            )
        """))

        count = await self.session.scalar(text(
            "SELECT COUNT(*) FROM zone_intelligence WHERE total_contracts > 0"
        ))

        await self.session.flush()
        return {"enriched_zones": count or 0, "fields": [
            "total_contracts", "total_amount_bdt", "active_agencies", "avg_npp"
        ]}

    async def _enrich_discount_patterns(self) -> Dict[str, Any]:
        """Calculate and enrich discount patterns by agency, zone, and method."""
        await self.session.execute(text("DELETE FROM discount_patterns"))

        # Agency-level discount patterns
        await self.session.execute(text("""
            INSERT INTO discount_patterns (
                id, agency_code, zone_name, procurement_method,
                sample_size, avg_npp, min_npp, max_npp, median_npp, stddev_npp,
                total_amount_bdt, created_at, updated_at
            )
            SELECT
                substr(md5('pattern:' || COALESCE(agency_code, 'all') || ':' ||
                    COALESCE(zone_name, 'all') || ':' ||
                    COALESCE(procurement_method, 'all')), 1, 36),
                agency_code,
                zone_name,
                procurement_method,
                COUNT(*)::int AS sample_size,
                COALESCE(AVG(NULLIF(npp_ratio, 0)), 0)::float AS avg_npp,
                COALESCE(MIN(NULLIF(npp_ratio, 0)), 0)::float AS min_npp,
                COALESCE(MAX(NULLIF(npp_ratio, 0)), 0)::float AS max_npp,
                COALESCE(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY NULLIF(npp_ratio, 0)), 0)::float AS median_npp,
                COALESCE(STDDEV_POP(NULLIF(npp_ratio, 0)), 0)::float AS stddev_npp,
                COALESCE(SUM(award_amount_bdt), 0)::float AS total_amount_bdt,
                now(), now()
            FROM procurement_lifecycle
            WHERE winner IS NOT NULL AND award_amount_bdt > 0
            GROUP BY GROUPING SETS (
                (agency_code, zone_name, procurement_method),
                (agency_code, zone_name),
                (agency_code, procurement_method),
                (zone_name, procurement_method),
                (agency_code),
                (zone_name),
                (procurement_method),
                ()
            )
            HAVING COUNT(*) >= 2
        """))

        count = await self.session.scalar(text(
            "SELECT COUNT(*) FROM discount_patterns"
        ))

        await self.session.flush()
        return {"discount_patterns": count or 0}

    async def _enrich_award_intelligence(self) -> Dict[str, Any]:
        """Populate award intelligence with quarterly/annual aggregates."""
        await self.session.execute(text("DELETE FROM award_intelligence"))

        await self.session.execute(text("""
            INSERT INTO award_intelligence (
                id, agency_code, fiscal_year, quarter,
                total_contracts, total_amount_bdt, avg_npp, avg_contract_amount,
                created_at, updated_at
            )
            SELECT
                substr(md5('award:' || COALESCE(agency_code, 'all') || ':' ||
                    COALESCE(fiscal_year, '0000') || ':q' ||
                    COALESCE(quarter, 0)::text), 1, 36),
                agency_code,
                fiscal_year,
                quarter,
                COUNT(*)::int AS total_contracts,
                COALESCE(SUM(award_amount_bdt), 0)::float AS total_amount_bdt,
                COALESCE(AVG(NULLIF(npp_ratio, 0)), 0)::float AS avg_npp,
                COALESCE(AVG(award_amount_bdt), 0)::float AS avg_contract_amount,
                now(), now()
            FROM (
                SELECT
                    agency_code,
                    TO_CHAR(award_date, 'YYYY') AS fiscal_year,
                    EXTRACT(QUARTER FROM award_date)::int AS quarter,
                    award_amount_bdt,
                    npp_ratio
                FROM procurement_lifecycle
                WHERE award_date IS NOT NULL AND award_amount_bdt > 0
            ) AS lifecycle_data
            GROUP BY GROUPING SETS (
                (agency_code, fiscal_year, quarter),
                (fiscal_year, quarter),
                ()
            )
        """))

        count = await self.session.scalar(text(
            "SELECT COUNT(*) FROM award_intelligence"
        ))

        await self.session.flush()
        return {"award_intelligence_records": count or 0}

    async def get_enrichment_summary(self) -> Dict[str, Any]:
        """Get summary of enriched intelligence data."""
        return {
            "contractors_with_profiles": await self.session.scalar(
                text("SELECT COUNT(*) FROM contractor_dna WHERE health_score > 0")
            ),
            "contractors_with_win_rate": await self.session.scalar(
                text("SELECT COUNT(*) FROM contractor_dna WHERE win_rate > 0")
            ),
            "contractors_with_completion": await self.session.scalar(
                text("SELECT COUNT(*) FROM contractor_dna WHERE completion_rate > 0")
            ),
            "agencies_enriched": await self.session.scalar(
                text("SELECT COUNT(*) FROM agency_intelligence WHERE total_contracts > 0")
            ),
            "zones_enriched": await self.session.scalar(
                text("SELECT COUNT(*) FROM zone_intelligence WHERE total_contracts > 0")
            ),
            "discount_patterns": await self.session.scalar(
                text("SELECT COUNT(*) FROM discount_patterns")
            ),
            "award_intelligence_records": await self.session.scalar(
                text("SELECT COUNT(*) FROM award_intelligence")
            ),
        }

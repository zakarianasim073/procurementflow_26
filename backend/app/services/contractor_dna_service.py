"""
Contractor DNA Service
Contractor profiling, search, benchmarking, and DNA building.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.intelligence_base import IntelligenceBaseService

logger = logging.getLogger(__name__)


class ContractorDNAService(IntelligenceBaseService):
    """
    Contractor import, DNA rebuild, search, and benchmarking.
    """

    async def import_contractors_from_json(self, data: List[Dict]) -> Dict[str, Any]:
        """Import contractors.json into Contractor table."""
        from app.models.intelligence import Contractor
        imported = 0
        for item in data:
            name = self._normalize_contractor_name(item.get("contractor_name") or item.get("name", ""))
            if not name or self._should_exclude_contractor_name(name):
                continue
            contractor = Contractor(
                id=self._uuid(),
                contractor_name=name[:300],
                total_contracts=int(item.get("total_contracts") or item.get("total_wins") or 0),
                total_amount_bdt=self._safe_float(item.get("total_amount_bdt")) or 0.0,
                agencies_worked=item.get("agencies") or [],
                districts_worked=item.get("districts") or [],
                avg_npp=self._safe_float(item.get("avg_npp")) or 0.0,
                created_at=datetime.now(timezone.utc),
            )
            self.session.add(contractor)
            imported += 1
        await self.session.flush()
        return {"imported": imported, "total": len(data)}

    async def rebuild_contractor_intelligence(self) -> Dict[str, Any]:
        """Rebuild contractor DNA from lifecycle winners and opening-report bidders."""
        await self.session.execute(text("""
            INSERT INTO contractors (
                id, contractor_name, total_contracts, total_amount_bdt,
                agencies_worked, districts_worked, avg_npp,
                first_award_date, last_award_date, created_at, updated_at
            )
            SELECT
                substr(md5(lower(trim(winner))), 1, 36) AS id,
                trim(winner) AS contractor_name,
                count(*)::int AS total_contracts,
                coalesce(sum(award_amount_bdt), 0)::float AS total_amount_bdt,
                to_json(array_remove(array_agg(DISTINCT agency_code), NULL)) AS agencies_worked,
                to_json(array_remove(array_agg(DISTINCT zone_name), NULL)) AS districts_worked,
                coalesce(avg(NULLIF(npp_ratio, 0)), 0)::float AS avg_npp,
                min(award_date) AS first_award_date,
                max(award_date) AS last_award_date,
                now(), now()
            FROM procurement_lifecycle
            WHERE winner IS NOT NULL AND trim(winner) <> ''
            GROUP BY lower(trim(winner)), trim(winner)
            ON CONFLICT (contractor_name) DO UPDATE SET
                total_contracts = EXCLUDED.total_contracts,
                total_amount_bdt = EXCLUDED.total_amount_bdt,
                agencies_worked = EXCLUDED.agencies_worked,
                districts_worked = EXCLUDED.districts_worked,
                avg_npp = EXCLUDED.avg_npp,
                first_award_date = EXCLUDED.first_award_date,
                last_award_date = EXCLUDED.last_award_date,
                updated_at = now()
        """))

        await self.session.execute(text("DELETE FROM contractor_dna"))
        await self.session.execute(text("""
            WITH award_stats AS (
                SELECT
                    lower(trim(winner)) AS name_key,
                    count(*)::int AS total_contracts,
                    coalesce(sum(award_amount_bdt), 0)::float AS total_amount_bdt,
                    coalesce(avg(NULLIF(award_amount_bdt, 0)), 0)::float AS avg_award_bdt,
                    count(DISTINCT agency_code)::int AS agencies_worked,
                    count(DISTINCT zone_name)::int AS districts_worked,
                    coalesce(avg(NULLIF(npp_ratio, 0)), 0)::float AS avg_npp,
                    coalesce(stddev_pop(NULLIF(npp_ratio, 0)), 0)::float AS npp_volatility,
                    min(award_date) AS first_award_date,
                    max(award_date) AS last_award_date,
                    count(CASE WHEN contract_status = 'Completed' THEN 1 END)::int AS completed_count,
                    count(CASE WHEN contract_status = 'On-time' THEN 1 END)::int AS on_time_count,
                    coalesce(avg(NULLIF(delay_days, 0)), 0)::float AS avg_delay_days
                FROM procurement_lifecycle
                WHERE winner IS NOT NULL AND trim(winner) <> ''
                GROUP BY lower(trim(winner))
            ),
            preferred_agency AS (
                SELECT DISTINCT ON (lower(trim(winner)))
                    lower(trim(winner)) AS name_key, agency_code
                FROM procurement_lifecycle
                WHERE winner IS NOT NULL AND trim(winner) <> '' AND agency_code IS NOT NULL
                GROUP BY lower(trim(winner)), agency_code
                ORDER BY lower(trim(winner)), count(*) DESC
            ),
            preferred_zone AS (
                SELECT DISTINCT ON (lower(trim(winner)))
                    lower(trim(winner)) AS name_key, zone_name
                FROM procurement_lifecycle
                WHERE winner IS NOT NULL AND trim(winner) <> '' AND zone_name IS NOT NULL
                GROUP BY lower(trim(winner)), zone_name
                ORDER BY lower(trim(winner)), count(*) DESC
            )
            INSERT INTO contractor_dna (
                id, contractor_id, total_contracts, total_amount_bdt, avg_award_bdt,
                agencies_worked, districts_worked, preferred_agency, preferred_zone,
                avg_npp, npp_volatility, win_rate, avg_discount_pct,
                completion_rate, on_time_rate, avg_delay_days,
                first_award_date, last_award_date, health_score, created_at, updated_at
            )
            SELECT
                substr(md5('dna-v1:' || c.id), 1, 36),
                c.id,
                a.total_contracts,
                a.total_amount_bdt,
                a.avg_award_bdt,
                a.agencies_worked,
                a.districts_worked,
                pa.agency_code,
                pz.zone_name,
                a.avg_npp,
                a.npp_volatility,
                least(100.0, (a.total_contracts::float / greatest(a.total_contracts, 1)) * 100.0),
                greatest(0.0, (1.0 - a.avg_npp) * 100.0),
                least(100.0, greatest(0.0, (a.completed_count::float / greatest(a.total_contracts, 1)) * 100.0)),
                least(100.0, greatest(0.0, (a.on_time_count::float / greatest(a.total_contracts, 1)) * 100.0)),
                greatest(0.0, a.avg_delay_days),
                a.first_award_date,
                a.last_award_date,
                least(1.0, greatest(0.35,
                    0.35 +
                    (least(a.total_contracts, 100) / 200.0) +
                    (least(a.total_amount_bdt, 1000000000) / 5000000000.0) +
                    (greatest(0.0, (a.completed_count::float / greatest(a.total_contracts, 1)) * 100.0)) / 250.0 +
                    (greatest(0.0, (a.on_time_count::float / greatest(a.total_contracts, 1)) * 100.0)) / 250.0
                )),
                now(), now()
            FROM contractors c
            JOIN award_stats a ON a.name_key = lower(trim(c.contractor_name))
            LEFT JOIN preferred_agency pa ON pa.name_key = a.name_key
            LEFT JOIN preferred_zone pz ON pz.name_key = a.name_key
        """))

        rebuilt_v1 = int(await self.session.scalar(text("SELECT count(*) FROM contractor_dna")) or 0)
        rebuilt_v2 = await self._rebuild_contractor_dna_v2()
        await self.session.flush()
        return {"rebuilt": rebuilt_v1, "rebuilt_v2": rebuilt_v2}

    async def _rebuild_contractor_dna_v2(self) -> int:
        exists = await self.session.scalar(text("SELECT to_regclass('public.contractor_dna_v2')"))
        if not exists:
            return 0

        await self.session.execute(text("DELETE FROM contractor_dna_v2"))
        await self.session.execute(text("""
            WITH award_stats AS (
                SELECT
                    lower(trim(winner)) AS name_key,
                    count(*)::int AS total_wins,
                    coalesce(sum(award_amount_bdt), 0)::float AS total_award_amount_bdt,
                    coalesce(avg(NULLIF(award_amount_bdt, 0)), 0)::float AS avg_award_amount_bdt,
                    coalesce(avg(greatest(0.0, (1.0 - NULLIF(npp_ratio, 0)) * 100.0)), 0)::float AS award_avg_discount,
                    coalesce(stddev_pop(greatest(0.0, (1.0 - NULLIF(npp_ratio, 0)) * 100.0)), 0)::float AS award_discount_stddev,
                    coalesce(avg(NULLIF(npp_ratio, 0)), 0)::float AS avg_npp
                FROM procurement_lifecycle
                WHERE winner IS NOT NULL AND trim(winner) <> ''
                GROUP BY lower(trim(winner))
            ),
            agency_counts AS (
                SELECT lower(trim(winner)) AS name_key, coalesce(agency_code, 'unknown') AS key, count(*)::int AS cnt
                FROM procurement_lifecycle
                WHERE winner IS NOT NULL AND trim(winner) <> ''
                GROUP BY lower(trim(winner)), coalesce(agency_code, 'unknown')
            ),
            agency_aff AS (
                SELECT name_key, jsonb_object_agg(key, cnt) AS agency_affinity
                FROM agency_counts GROUP BY name_key
            ),
            zone_counts AS (
                SELECT lower(trim(winner)) AS name_key, coalesce(zone_name, 'unknown') AS key, count(*)::int AS cnt
                FROM procurement_lifecycle
                WHERE winner IS NOT NULL AND trim(winner) <> ''
                GROUP BY lower(trim(winner)), coalesce(zone_name, 'unknown')
            ),
            zone_aff AS (
                SELECT name_key, jsonb_object_agg(key, cnt) AS zone_affinity
                FROM zone_counts GROUP BY name_key
            ),
            opening_raw AS (
                SELECT
                    lower(trim(coalesce(
                        bidder->>'name', bidder->>'bidder_name', bidder->>'contractor_name', bidder->>'winner'
                    ))) AS name_key,
                    COALESCE(NULLIF(regexp_replace(coalesce(bidder->>'rank', ''), '[^0-9]', '', 'g'), '')::int, ordinality::int) AS bid_rank,
                    lower(coalesce(
                        bidder->>'status', bidder->>'financial_status', bidder->>'evaluation_status', 'responsive'
                    )) AS status_text,
                    o.has_slt,
                    NULLIF(regexp_replace(coalesce(
                        bidder->>'discount_pct', bidder->>'discount', bidder->>'discount_percent', ''
                    ), '[^0-9.-]', '', 'g'), '')::float AS explicit_discount,
                    NULLIF(regexp_replace(coalesce(
                        bidder->>'final_amount', bidder->>'net_quoted', bidder->>'quoted_amount',
                        bidder->>'amount', bidder->>'bid_amount', ''
                    ), '[^0-9.-]', '', 'g'), '')::float AS quoted_amount,
                    o.estimated_amount_bdt::float AS estimate
                FROM opening_reports o
                CROSS JOIN LATERAL jsonb_array_elements(
                    CASE WHEN jsonb_typeof(o.bidders::jsonb) = 'array' THEN o.bidders::jsonb ELSE '[]'::jsonb END
                ) WITH ORDINALITY AS b(bidder, ordinality)
                WHERE coalesce(bidder->>'name', bidder->>'bidder_name', bidder->>'contractor_name', bidder->>'winner') IS NOT NULL
            ),
            opening_stats AS (
                SELECT
                    name_key,
                    count(*)::int AS total_bids,
                    avg(bid_rank)::float AS avg_rank,
                    avg(CASE WHEN status_text LIKE '%non%' OR status_text LIKE '%reject%' THEN 0.0 ELSE 1.0 END)::float AS responsive_rate,
                    avg(CASE WHEN status_text LIKE '%non%' OR status_text LIKE '%reject%' THEN 1.0 ELSE 0.0 END)::float AS non_responsive_rate,
                    avg(CASE WHEN has_slt THEN 1.0 ELSE 0.0 END)::float AS slt_rate,
                    avg(coalesce(explicit_discount, CASE WHEN estimate > 0 AND quoted_amount > 0 THEN (1.0 - quoted_amount / estimate) * 100.0 END))::float AS opening_avg_discount,
                    coalesce(stddev_pop(coalesce(explicit_discount, CASE WHEN estimate > 0 AND quoted_amount > 0 THEN (1.0 - quoted_amount / estimate) * 100.0 END)), 0)::float AS opening_discount_stddev
                FROM opening_raw
                WHERE name_key IS NOT NULL AND name_key <> ''
                GROUP BY name_key
            )
            INSERT INTO contractor_dna_v2 (
                id, contractor_id, contractor_name, total_bids, total_wins, win_rate,
                avg_discount, discount_stddev, avg_rank, responsive_rate, slt_rate,
                non_responsive_rate, agency_affinity, zone_affinity, project_type_affinity,
                total_award_amount_bdt, avg_award_amount_bdt, nppi_score,
                aggression_index, reliability_index, adaptation_score, health_score,
                last_rebuilt_at, created_at, updated_at
            )
            SELECT
                substr(md5('dna-v2:' || c.id), 1, 36),
                c.id,
                c.contractor_name,
                coalesce(o.total_bids, 0),
                coalesce(a.total_wins, 0),
                CASE WHEN coalesce(o.total_bids, 0) > 0 THEN coalesce(a.total_wins, 0)::float / o.total_bids ELSE 0.0 END,
                coalesce(o.opening_avg_discount, a.award_avg_discount, 0.0),
                coalesce(o.opening_discount_stddev, a.award_discount_stddev, 0.0),
                coalesce(o.avg_rank, 0.0),
                coalesce(o.responsive_rate, 0.0),
                coalesce(o.slt_rate, 0.0),
                coalesce(o.non_responsive_rate, 0.0),
                coalesce(aa.agency_affinity, '{}'::jsonb),
                coalesce(za.zone_affinity, '{}'::jsonb),
                '{}'::jsonb,
                coalesce(a.total_award_amount_bdt, 0.0),
                coalesce(a.avg_award_amount_bdt, 0.0),
                greatest(0.0, (1.0 - coalesce(a.avg_npp, 1.0)) * 100.0),
                least(100.0, greatest(0.0, coalesce(o.opening_avg_discount, a.award_avg_discount, 0.0) * 5.0)),
                least(100.0, greatest(0.0, coalesce(o.responsive_rate, 0.0) * 100.0)),
                least(100.0, sqrt(greatest(coalesce(o.total_bids, a.total_wins, 0), 0)) * 10.0),
                least(100.0,
                    coalesce(o.responsive_rate, 0.0) * 45.0
                    + least(coalesce(a.total_wins, 0), 100) * 0.25
                    + least(coalesce(a.total_award_amount_bdt, 0.0), 1000000000.0) / 20000000.0
                    + (1.0 - coalesce(o.non_responsive_rate, 0.0)) * 20.0
                ),
                now(), now(), now()
            FROM contractors c
            LEFT JOIN award_stats a ON a.name_key = lower(trim(c.contractor_name))
            LEFT JOIN opening_stats o ON o.name_key = lower(trim(c.contractor_name))
            LEFT JOIN agency_aff aa ON aa.name_key = lower(trim(c.contractor_name))
            LEFT JOIN zone_aff za ON za.name_key = lower(trim(c.contractor_name))
            WHERE coalesce(a.total_wins, 0) > 0 OR coalesce(o.total_bids, 0) > 0
        """))
        return int(await self.session.scalar(text("SELECT count(*) FROM contractor_dna_v2")) or 0)

    async def list_contractors(self, limit: int = 100) -> List[Dict]:
        """Contractor listing."""
        from app.models.intelligence import Contractor
        from sqlalchemy import select

        stmt = select(Contractor).limit(limit)
        result = await self.session.execute(stmt)
        return [self._contractor_to_dict(c) for c in result.scalars().all()]

    async def get_contractor(self, contractor_id: str) -> Optional[Dict]:
        """Single contractor lookup."""
        from app.models.intelligence import Contractor
        from sqlalchemy import select

        stmt = select(Contractor).where(Contractor.id == contractor_id)
        result = await self.session.execute(stmt)
        contractor = result.scalar_one_or_none()
        return self._contractor_to_dict(contractor) if contractor else None

    async def search_contractors(self, query: str, limit: int = 50) -> List[Dict]:
        """Fuzzy contractor search."""
        from app.models.intelligence import Contractor
        from sqlalchemy import select, or_

        q = f"%{query}%"
        stmt = select(Contractor).where(
            Contractor.contractor_name.ilike(q)
        ).limit(limit)
        result = await self.session.execute(stmt)
        return [self._contractor_to_dict(c) for c in result.scalars().all()]

    async def get_contractor_stats(self) -> Dict[str, Any]:
        """Global contractor stats."""
        from app.models.intelligence import Contractor
        from sqlalchemy import select, func

        total = await self.session.execute(select(func.count(Contractor.id)))
        return {"total_contractors": total.scalar()}

    async def get_contractor_dna(self, contractor_id: str) -> Optional[Dict]:
        """ContractorDNA row fetch."""
        from app.models.intelligence import ContractorDNA
        from sqlalchemy import select

        stmt = select(ContractorDNA).where(ContractorDNA.contractor_id == contractor_id)
        result = await self.session.execute(stmt)
        dna = result.scalar_one_or_none()
        if not dna:
            return None
        return {
            "contractor_id": dna.contractor_id,
            "total_contracts": dna.total_contracts,
            "total_amount_bdt": dna.total_amount_bdt,
            "avg_award_bdt": dna.avg_award_bdt,
            "avg_npp": dna.avg_npp,
        }

    async def benchmark_contractor(self, contractor_id: str) -> Optional[Dict]:
        """Percentile benchmarking against peers."""
        from app.models.intelligence import ContractorDNA
        from sqlalchemy import select, func

        stmt = select(ContractorDNA).where(ContractorDNA.contractor_id == contractor_id)
        result = await self.session.execute(stmt)
        dna = result.scalar_one_or_none()
        if not dna or not dna.avg_npp:
            return None

        total = await self.session.execute(select(func.count(ContractorDNA.id)))
        total_count = total.scalar() or 1

        better = await self.session.execute(
            select(func.count(ContractorDNA.id)).where(ContractorDNA.avg_npp < dna.avg_npp)
        )
        better_count = better.scalar() or 0

        percentile = (better_count / total_count) * 100
        return {
            "contractor_id": contractor_id,
            "avg_npp": dna.avg_npp,
            "percentile": round(percentile, 2),
            "total_contractors": total_count,
        }

    # ── Internal helpers ─────────────────────────────────────────────────

    def _contractor_to_dict(self, c) -> Dict:
        return {
            "id": c.id,
            "contractor_name": c.contractor_name,
            "total_contracts": c.total_contracts,
            "total_amount_bdt": c.total_amount_bdt,
            "agencies_worked": c.agencies_worked,
            "districts_worked": c.districts_worked,
            "avg_npp": c.avg_npp,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }

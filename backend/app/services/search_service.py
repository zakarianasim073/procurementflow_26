"""Unified full-text search service.

Covers: tenders (procurement_lifecycle), awards (award_records_v2), contractors.
Uses PostgreSQL tsvector for FTS and pg_trgm for partial/fuzzy matching.
SQL is built conditionally to avoid asyncpg NULL-type inference issues.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class SearchService:

    @staticmethod
    async def search_tenders(
        db: AsyncSession,
        q: str,
        agency: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        scope: str = "live",
    ) -> Dict[str, Any]:
        q = q.strip()
        if scope == "live":
            return await SearchService.search_live_tenders(
                db, q, agency=agency, limit=limit, offset=offset
            )
        agency_clause = "AND agency_code = :agency" if agency else ""
        params: Dict[str, Any] = {"limit": limit + 1, "offset": offset}
        if agency:
            params["agency"] = agency

        # Collapse rows that describe the same package. procurement_lifecycle
        # stores package_no verbatim per source, so the same tender appears
        # several times under casing/punctuation variants
        # ('LGED/GOBM/Bag/25-26/RW-51' vs 'LGED/GOBM/BAG/25-26/RW-51') —
        # 88k of 658k rows. Grouping on the ADR-016 normalized key removes the
        # duplicates; the surviving row per key is the one carrying the most
        # complete cost/award data. Rows with no usable package_no fall back to
        # their id so they are never merged together.
        # Some sources publish the award in crore rather than taka, so ~10.7k
        # rows hold values like 0.474 that are really 0.474 Cr. Against packages
        # with a known-taka estimate the median estimate/award ratio for these
        # is 1.1e7, confirming the factor. Values in the 10..1000 band show no
        # consistent ratio (median 600), so they are left untouched rather than
        # guessed at.
        award_bdt = (
            "CASE WHEN award_amount_bdt > 0 AND award_amount_bdt < 10 "
            "THEN award_amount_bdt * 1e7 ELSE award_amount_bdt END AS award_amount_bdt"
        )

        if q:
            params["q"] = q
            stmt = text(f"""
                SELECT DISTINCT ON (
                    COALESCE(NULLIF(REGEXP_REPLACE(REGEXP_REPLACE(UPPER(package_no),
                        '\\s+', '', 'g'), '[^A-Z0-9/.\\-]', '', 'g'), ''), 'ID:' || id::text)
                )
                    package_no, tender_id, agency_code, zone_name, title,
                    estimated_cost_bdt, {award_bdt}, winner, award_date,
                    ts_rank_cd(
                        to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(package_no,'')),
                        websearch_to_tsquery('simple', :q)
                    ) AS rank
                FROM procurement_lifecycle
                WHERE to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(package_no,''))
                      @@ websearch_to_tsquery('simple', :q)
                {agency_clause}
                ORDER BY
                    COALESCE(NULLIF(REGEXP_REPLACE(REGEXP_REPLACE(UPPER(package_no),
                        '\\s+', '', 'g'), '[^A-Z0-9/.\\-]', '', 'g'), ''), 'ID:' || id::text),
                    (COALESCE(estimated_cost_bdt, 0) > 0) DESC,
                    (COALESCE(award_amount_bdt, 0) > 0) DESC,
                    award_date DESC NULLS LAST,
                    id
                LIMIT :limit OFFSET :offset
            """)
        else:
            # Fast path: no FTS needed. Use indexed award_date scan with simple
            # dedup via DISTINCT ON (package_no normalized). Avoids the full
            # ROW_NUMBER window function over 658K rows.
            stmt = text(f"""
                SELECT DISTINCT ON (
                    COALESCE(NULLIF(REGEXP_REPLACE(REGEXP_REPLACE(UPPER(package_no),
                        '\\s+', '', 'g'), '[^A-Z0-9/.\\-]', '', 'g'), ''), 'ID:' || id::text)
                )
                    package_no, tender_id, agency_code, zone_name, title,
                    estimated_cost_bdt, {award_bdt}, winner, award_date, 0.0 AS rank
                FROM procurement_lifecycle
                WHERE award_date IS NOT NULL {agency_clause}
                ORDER BY
                    COALESCE(NULLIF(REGEXP_REPLACE(REGEXP_REPLACE(UPPER(package_no),
                        '\\s+', '', 'g'), '[^A-Z0-9/.\\-]', '', 'g'), ''), 'ID:' || id::text),
                    (COALESCE(estimated_cost_bdt, 0) > 0) DESC,
                    award_date DESC NULLS LAST
                LIMIT :limit OFFSET :offset
            """)

        try:
            result = await db.execute(stmt, params)
            rows = [dict(r) for r in result.mappings()]
        except Exception:
            logger.exception("tender search failed")
            rows = []
        has_more = len(rows) > limit
        return _page(rows[:limit], q, limit, offset, has_more, "tenders")

    @staticmethod
    async def search_live_tenders(
        db: AsyncSession,
        q: str,
        agency: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Browse current e-GP Works notices stored by the live Radar feed."""
        clauses = [
            "t.closing_datetime > now()",
            "coalesce(t.is_deleted, false) = false",
            """(
                lower(coalesce(t.category, '')) = 'works'
                OR lower(coalesce(t.procurement_nature, '')) = 'works'
                OR lower(coalesce(t.title, '')) LIKE 'works,%'
            )""",
        ]
        params: Dict[str, Any] = {"limit": limit + 1, "offset": offset}
        if agency:
            clauses.append("upper(t.agency_code) = :agency")
            params["agency"] = agency.upper()
        if q:
            clauses.append("""(
                t.title ILIKE :q_like OR t.package_no ILIKE :q_like
                OR t.tender_id ILIKE :q_like OR t.pe_office ILIKE :q_like
            )""")
            params["q_like"] = f"%{q}%"
        where_sql = " AND ".join(clauses)
        normalized_tender = (
            r"REGEXP_REPLACE(REGEXP_REPLACE(UPPER(COALESCE(t.package_no,'')), "
            r"'\\s+', '', 'g'), '[^A-Z0-9/.\\-]', '', 'g')"
        )
        total = (await db.execute(
            text(f"SELECT count(*) FROM pf_tenders t WHERE {where_sql}"), params
        )).scalar_one()
        rows = (await db.execute(text(f"""
            WITH candidates AS (
                SELECT t.*
                FROM pf_tenders t
                WHERE {where_sql}
                ORDER BY t.closing_datetime, t.tender_id
                LIMIT :limit OFFSET :offset
            )
            SELECT
                t.package_no, t.tender_id, coalesce(t.agency_code, 'UNKNOWN') AS agency_code,
                t.district AS zone_name, t.title,
                coalesce(app.estimated_cost_bdt, 0)::float AS estimated_cost_bdt,
                NULL::float AS award_amount_bdt, NULL::text AS winner,
                NULL::text AS award_date, 1.0::float AS rank,
                t.closing_datetime AS closing_date, 'egp_live' AS source
                , req.tender_security_amount_bdt, req.tender_security_text
            FROM candidates t
            LEFT JOIN LATERAL (
                SELECT CASE
                    WHEN a.estimated_cost_bdt > 0 AND a.estimated_cost_bdt < 10
                        THEN a.estimated_cost_bdt * 10000000
                    ELSE a.estimated_cost_bdt
                END AS estimated_cost_bdt
                FROM app_records a
                WHERE a.normalized_package_no = {normalized_tender}
                  AND lower(coalesce(a.category, 'works')) = 'works'
                ORDER BY a.updated_at DESC NULLS LAST
                LIMIT 1
            ) app ON true
            LEFT JOIN LATERAL (
                SELECT
                    coalesce(
                        nullif(k.data #>> '{{payload,tender_security_amount_bdt}}', '')::numeric,
                        nullif(k.data ->> 'tender_security_amount_bdt', '')::numeric
                    )::float AS tender_security_amount_bdt,
                    coalesce(
                        k.data #>> '{{payload,tender_security_text}}',
                        k.data ->> 'tender_security_text'
                    ) AS tender_security_text
                FROM knowledge_entries k
                WHERE k.tender_id = t.tender_id
                  AND k.entry_type = 'tender_requirement_enrichment'
                  AND coalesce(k.is_archived, false) = false
                ORDER BY k.updated_at DESC
                LIMIT 1
            ) req ON true
            ORDER BY t.closing_datetime, t.tender_id
        """), params)).mappings().all()
        data = [dict(row) for row in rows]
        has_more = len(data) > limit
        page = _page(data[:limit], q, limit, offset, has_more, "live_tenders")
        page["count"] = int(total)
        return page

    @staticmethod
    async def search_awards(
        db: AsyncSession,
        q: str,
        district: Optional[str] = None,
        contractor: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        q = q.strip()
        clauses: List[str] = []
        params: Dict[str, Any] = {"limit": limit + 1, "offset": offset}
        if district:
            clauses.append("district ILIKE :district")
            params["district"] = f"%{district}%"
        if contractor:
            clauses.append("contractor_name ILIKE :contractor")
            params["contractor"] = f"%{contractor}%"
        filter_sql = ("AND " + " AND ".join(clauses)) if clauses else ""

        if q:
            params["q"] = q
            stmt = text(f"""
                SELECT
                    id, title, contractor_name, procuring_entity,
                    amount_bdt, estimated_amount_bdt, district, agency_code,
                    award_date, package_no,
                    ts_rank_cd(
                        to_tsvector('simple',
                            coalesce(title,'') || ' ' ||
                            coalesce(contractor_name,'') || ' ' ||
                            coalesce(procuring_entity,'')
                        ),
                        websearch_to_tsquery('simple', :q)
                    ) AS rank
                FROM award_records_v2
                WHERE to_tsvector('simple',
                          coalesce(title,'') || ' ' ||
                          coalesce(contractor_name,'') || ' ' ||
                          coalesce(procuring_entity,'')
                      ) @@ websearch_to_tsquery('simple', :q)
                {filter_sql}
                ORDER BY rank DESC, award_date DESC NULLS LAST
                LIMIT :limit OFFSET :offset
            """)
        else:
            stmt = text(f"""
                SELECT
                    id, title, contractor_name, procuring_entity,
                    amount_bdt, estimated_amount_bdt, district, agency_code,
                    award_date, package_no, 0.0 AS rank
                FROM award_records_v2
                WHERE 1=1 {filter_sql}
                ORDER BY award_date DESC NULLS LAST
                LIMIT :limit OFFSET :offset
            """)

        try:
            result = await db.execute(stmt, params)
            rows = [dict(r) for r in result.mappings()]
        except Exception:
            logger.exception("award search failed")
            rows = []
        has_more = len(rows) > limit
        return _page(rows[:limit], q, limit, offset, has_more, "awards")

    @staticmethod
    async def search_contractors(
        db: AsyncSession,
        q: str,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        q = q.strip()
        params: Dict[str, Any] = {"limit": limit + 1, "offset": offset}

        if q:
            params["q"] = q
            params["q_like"] = f"%{q}%"
            stmt = text("""
                SELECT
                    id, contractor_name, total_contracts, total_amount_bdt,
                    avg_npp, last_award_date,
                    ts_rank_cd(
                        to_tsvector('simple', coalesce(contractor_name,'')),
                        websearch_to_tsquery('simple', :q)
                    ) AS rank
                FROM contractors
                WHERE to_tsvector('simple', coalesce(contractor_name,''))
                          @@ websearch_to_tsquery('simple', :q)
                   OR contractor_name ILIKE :q_like
                ORDER BY rank DESC, total_amount_bdt DESC NULLS LAST
                LIMIT :limit OFFSET :offset
            """)
        else:
            stmt = text("""
                SELECT
                    id, contractor_name, total_contracts, total_amount_bdt,
                    avg_npp, last_award_date, 0.0 AS rank
                FROM contractors
                ORDER BY total_amount_bdt DESC NULLS LAST
                LIMIT :limit OFFSET :offset
            """)

        try:
            result = await db.execute(stmt, params)
            rows = [dict(r) for r in result.mappings()]
        except Exception:
            logger.exception("contractor search failed")
            rows = []
        has_more = len(rows) > limit
        return _page(rows[:limit], q, limit, offset, has_more, "contractors")

    @staticmethod
    async def search_global(
        db: AsyncSession,
        q: str,
        limit_per_type: int = 10,
    ) -> Dict[str, Any]:
        t = await SearchService.search_tenders(db, q, limit=limit_per_type)
        a = await SearchService.search_awards(db, q, limit=limit_per_type)
        c = await SearchService.search_contractors(db, q, limit=limit_per_type)
        return {
            "success": True,
            "query": q,
            "tenders": t["data"],
            "awards": a["data"],
            "contractors": c["data"],
            "counts": {
                "tenders": t["count"],
                "awards": a["count"],
                "contractors": c["count"],
            },
        }


def _page(
    rows: List[Dict],
    q: str,
    limit: int,
    offset: int,
    has_more: bool,
    entity_type: str,
) -> Dict[str, Any]:
    return {
        "success": True,
        "query": q,
        "entity_type": entity_type,
        "limit": limit,
        "offset": offset,
        "has_more": has_more,
        "next_offset": offset + limit if has_more else None,
        "data": rows,
        "count": len(rows),
    }
